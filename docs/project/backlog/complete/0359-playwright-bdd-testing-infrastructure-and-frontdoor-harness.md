---
id: 0359
title: Playwright BDD Testing Infrastructure and Frontdoor Harness
status: Complete
created: 2026-09-28
dependencies:
- TASK-0004
- TASK-0010
- TASK-0352
governing_adrs:
- ADR-0004
- ADR-0010
- ADR-0013
- ADR-0014
governing_prds:
- PRD-0023
governing_stories:
- US-0063
- US-0065
target_release: 0.9.0
pr_url: https://github.com/tyevans/runefoble/pull/356
---
# TASK-0359: Playwright BDD Testing Infrastructure and Frontdoor Harness

## Status
Refined

## Summary
Establish the foundational Playwright BDD testing infrastructure and frontdoor test harness for the Runefoble monorepo per ADR-0014. Configure `@playwright/test` and a Gherkin-compatible step runner, set up `playwright.config.ts` targeting local dev servers (`http://localhost:5173` and `http://localhost:8000`), implement public frontdoor authentication and data-setup fixtures, and provide developer `Makefile` targets (`test-e2e`, `test-e2e-ui`, `test-bdd`).

## Problem Statement
Runefoble's user interfaces span decoupled Lit Web Component microfrontends communicating across Shadow DOM boundaries, WebSocket connections, and REST APIs. While Python pytest integration tests exist for backend routes and Storybook tests exist for isolated components, there is no end-to-end browser automation framework verifying real user journeys. 

Integration bugs—such as dead-end tabs with `e.preventDefault()`, unhandled CustomEvents on microfrontends, and static fallback arrays masking 502 proxy errors—pass through unit tests undetected. To validate real user flows while strictly adhering to Hard Invariant 7 (Blackbox TDD with frontdoor setup), the repository requires a Playwright test runner driven by Gherkin scenarios with zero backdoor database manipulations.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/tutorials/01-local-development-setup.md`: Local development ports, Vite frontend, and API Gateway.
  - `docs/reference/ports-and-endpoints.md`: Ingress routing table and service endpoints.
  - `docs/how-to/navigate-client-spa-routes-and-breadcrumbs.md`: Client hash SPA routing patterns.
- **Governing Architecture & ADRs**:
  - **ADR-0004: Lit Web Components and Storybook UI**: Shadow DOM encapsulation and Custom Element rendering.
  - **ADR-0010: Continuous Integration and Deployment Gates**: Quality gates for automated verification.
  - **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Public frontdoor interfaces and manifest discovery.
  - **ADR-0014: Behavior-Driven Development (BDD) with Gherkin User Stories and Playwright End-to-End Validation**: Governing BDD standard and frontdoor-only testing invariant.

## Scope of Work & Implementation Plan
1. **Package Installation & Workspace Configuration**:
   - Add `@playwright/test` and `playwright-bdd` (or cucumber step loader) to root `devDependencies` or `frontend/package.json`.
   - Ensure browser download scripts are wired into pnpm scripts (`pnpm exec playwright install --with-deps chromium`).
2. **Playwright Configuration (`playwright.config.ts`)**:
   - Set `baseURL: 'http://localhost:5173'`.
   - Configure browser targets (Chromium default, Firefox, WebKit matrix).
   - Configure shadow-piercing locator preferences.
   - Enable automated failure artifacts: trace recording (`on-first-retry`), video capture on failure, and full-page screenshots.
   - Configure `webServer` or health check targeting `http://localhost:8000` (Gateway) and `http://localhost:5173` (Vite).
3. **Frontdoor Test Harness (`e2e/support/`)**:
   - `auth_fixtures.ts`: Frontdoor authentication utility injecting valid Zitadel JWT tokens into browser `localStorage` (`runefoble-access-token`, `runefoble-user`) without direct database tampering.
   - `frontdoor_api.ts`: Helper class executing public `/api/v1` REST requests to prepare preconditions (`Given campaign "X" exists`).
   - `world.ts`: Context storage for active test scenarios (current user, campaignId, sessionId).
4. **Core Step Definitions Library (`e2e/steps/`)**:
   - `common_steps.ts`:
     - `Given I am logged in as a {string}` (DM, Player, Spectator).
     - `When I navigate to {string}`.
     - `Then I should see the heading {string}`.
     - `Then the URL hash should be {string}`.
     - `Then I should see a toast notification containing {string}`.
5. **Developer Makefile Targets (`Makefile`)**:
   - `test-e2e`: Runs headless Playwright BDD suite across standard browsers.
   - `test-e2e-ui`: Launches interactive Playwright UI mode for live debugging.
   - `test-bdd`: Validates Gherkin feature syntax and step definition coverage.
6. **Smoke Test Scenario (`e2e/features/smoke.feature`)**:
   - Author a baseline Gherkin smoke feature verifying home landing, theme switcher, and navigation to campaigns dashboard.

## INVEST Criteria Evaluation
- **Independent (I)**: Establishes testing infrastructure without altering production runtime business logic.
- **Negotiable (N)**: Step definition naming conventions and runner tool choice can be tuned.
- **Valuable (V)**: Provides the foundational capability to execute Gherkin user stories in real browsers, eradicating integration blindspots.
- **Estimable (E)**: Standard Playwright and BDD configuration patterns.
- **Small (S)**: Confined to configuration, support fixtures, step library, and smoke feature (< 200 lines per module).
- **Testable (T)**: Tested by executing `make test-e2e` against the smoke feature with 100% passing results.

## Definition of Done
1. `@playwright/test` and BDD runner dependencies installed and managed via root pnpm workspace.
2. `playwright.config.ts` configured and successfully connects to `localhost:5173` and `localhost:8000`.
3. Frontdoor authentication fixture establishes authenticated user states without direct database access.
4. `make test-e2e` executes headless browser tests and passes the smoke scenario.
5. All source files strictly under 500 lines per Hard Invariant 6.
