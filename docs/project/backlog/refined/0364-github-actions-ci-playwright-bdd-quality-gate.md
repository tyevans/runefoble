---
id: '0364'
title: GitHub Actions CI Workflow Playwright BDD Quality Gate Integration
status: Refined
created: 2026-09-28
dependencies:
- TASK-0010
- TASK-0352
- TASK-0359
- TASK-0361
- TASK-0362
- TASK-0363
governing_adrs:
- ADR-0010
- ADR-0014
governing_prds:
- PRD-0023
governing_stories:
- US-0065
target_release: 0.9.0
---

# TASK-0364: GitHub Actions CI Workflow Playwright BDD Quality Gate Integration

## Status
Refined

## Summary
Integrate the Playwright BDD end-to-end test suite into the automated GitHub Actions CI pipeline (`.github/workflows/ci.yml`) as a blocking merge gate per ADR-0010 and ADR-0014. Configure Playwright browser caching, background service orchestration with readiness polling, headless test execution via `make test-e2e`, and automated failure artifact archiving (traces, screenshots, videos).

## Problem Statement
While unit tests, lint checks, and Storybook builds run automatically on every pull request, end-to-end browser user flows are not currently verified in CI. Regressions that break user navigation, real-time WebSocket state synchronization, or frontend API proxies can be merged into `main` without triggering CI failures.

To establish an unbreachable quality gate protecting core user flows, the CI workflow must execute the Playwright BDD suite against containerized or background local services on every pull request.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/reference/platform-services.md`: Platform services, container images, ports, and environment variables.
  - `docs/how-to/test-user-flows-with-playwright-bdd.md`: Running Playwright BDD test suites.
- **Governing Architecture & ADRs**:
  - **ADR-0010: Continuous Integration and Deployment Gates via GitHub Actions**: CI stages and blocking quality gates.
  - **ADR-0014: Behavior-Driven Development (BDD) with Gherkin User Stories and Playwright End-to-End Validation**: BDD testing framework.

## Scope of Work & Implementation Plan
1. **GitHub Actions Workflow Job (`.github/workflows/ci.yml`)**:
   - Add a new parallel or staged job: `e2e-playwright`:
     - Runs on `ubuntu-latest`.
     - Checks out code and sets up Node (v24) and Python (3.12 / uv).
     - Restores cached Playwright browser binaries from `~/.cache/ms-playwright`.
     - Installs Playwright system dependencies (`npx playwright install --with-deps chromium`).
2. **Service Orchestration & Readiness Polling**:
   - Launch local services in the background using `make dev` or Docker Compose / Kind:
     - Start Redis Streams and API Gateway.
     - Start Vite frontend.
     - Poll `http://localhost:8000/api/v1/health` and `http://localhost:5173` until `200 OK` is returned (max 60s timeout).
3. **Execution of Playwright BDD Suite**:
   - Execute `make test-e2e` in headless mode.
   - Run tests with `--reporter=github,html`.
4. **Failure Artifact Archiving**:
   - If tests fail, upload `playwright-report/`, traces, and video recordings using `actions/upload-artifact@v4` with a 14-day retention window.
5. **Local CI Emulation**:
   - Verify workflow locally using `act` or a local shell script simulating the GitHub Actions runner.

## INVEST Criteria Evaluation
- **Independent (I)**: Operates within CI configuration without modifying runtime application code.
- **Negotiable (N)**: Timeout durations, artifact retention policies, and browser matrix can be tuned.
- **Valuable (V)**: Automatically blocks any pull request that breaks core user stories or produces dead interface elements.
- **Estimable (E)**: Standard GitHub Actions YAML and Playwright CI patterns.
- **Small (S)**: Confined to `.github/workflows/ci.yml` (< 120 lines added).
- **Testable (T)**: Tested by running the workflow in GitHub Actions and confirming PR status checks.

## Definition of Done
1. `e2e-playwright` job exists in `.github/workflows/ci.yml`.
2. Browser caching successfully avoids re-downloading Playwright binaries on every run.
3. Tests run against background API Gateway and Vite instances without flakiness.
4. Failure traces and videos are properly archived and downloadable upon test failure.
5. All YAML and workflow files lint cleanly.
