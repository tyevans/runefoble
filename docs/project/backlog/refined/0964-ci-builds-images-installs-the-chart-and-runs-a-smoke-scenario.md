---
id: '0964'
title: CI Builds Images, Installs the Chart on Kind, and Runs a Smoke Scenario
status: Refined
created: 2026-11-19
dependencies:
- '0960'
- '0933'
governing_adrs:
- ADR-0005
- ADR-0010
- ADR-0014
governing_prds:
- PRD-0025
governing_stories: []
target_bc: core
target_release: 1.0.0
---

# TASK-0964: CI Builds Images, Installs the Chart on Kind, and Runs a Smoke Scenario

## Status

Refined. Release One hosting slice 13 (PRD-0025, outcome 6: CI builds the images, installs the chart in a cluster, and runs a smoke scenario). Writer C added dependency `0933`. Without it, `helm install --wait` deadlocks on the bucket hook, so the smoke job cannot pass.

## Summary

Add a CI job that builds every image, creates a Kind cluster, installs the chart with `--wait`, waits for `/readyz` on every service, and runs one Playwright scenario tagged `@smoke`. Add a second job that pushes images on `main` when a registry is set. The existing mock-SpiceDB e2e job stays as it is.

## Problem Statement

- `.github/workflows/ci.yml:101-116` (`helm-lint`) runs `helm lint` and `helm template` with default values only.
- `ci.yml:156-252` (`e2e-playwright`) runs against `make dev` with `SPICEDB_ENDPOINT: "mock"` (`ci.yml:217-218`, `:238-239`). No job runs against a real SpiceDB, and no job installs the chart.
- No CI job builds images (`make images` is not in the workflow). `Makefile:114-133` builds and loads them into Kind.
- `Makefile:153-158` (`helm-deploy`) loads `values.local.yaml` when it exists, and it does not use `--wait`. The smoke job needs an explicit command.
- `deployments/helm/runefoble/templates/silo-buckets-job.yaml:17` makes the bucket Job a post-install hook. Until record 0933 lands, `--wait` cannot finish on a fresh install.
- `.github/workflows/deploy-pages.yml` builds and deploys the documentation site. It runs no chart or image step.

## Documentation & Architecture Review

- ADR-0010 (`docs/project/adrs/accepted/adr-0010-continuous-integration-pipeline.md`): the CI pipeline. Add the jobs in the same style. Check ADR-0010 for the job naming and gate rules before you write the YAML.
- ADR-0005: CI installs the same chart that clusters use (no CI-only chart).
- ADR-0014 (`docs/project/adrs/accepted/adr-0014-bdd-gherkin-user-stories-and-playwright-e2e.md`): the smoke scenario is a Playwright BDD scenario with UI-only setup.
- `docs/reference/e2e-harness.md`: the Playwright harness, tags, and personas. Add the `@smoke` tag.
- `docs/reference/cli-interfaces.md`: lists `make images` and `make helm-deploy`. Document the CI use.

## Product & User Story References

- PRD-0025, Checkable Outcome 6 (CI builds images, installs the chart, runs a smoke scenario) and Checkable Outcome 3 (the full e2e suite passes twice on Kind; this record does not run the full suite).
- No user story. This is platform work.

## Detailed Specification & Implementation Plan

1. New job `kind-smoke` in `.github/workflows/ci.yml`:
   1. Check out the repository. Set up uv, Node, pnpm, and Helm (pin each version).
   2. Run `make images` (builds all images and loads them into the Kind cluster that the job creates).
   3. Create the Kind cluster with `deployments/kind/cluster-config.yaml`. Install Traefik with a pinned chart version (record 0960 pins it for the operator; the job uses the same pin).
   4. Install the chart: `helm upgrade --install runefoble deployments/helm/runefoble --wait --timeout 15m`. Do not pass `values.local.yaml`.
   5. Check `/readyz` for each service. Use `kubectl port-forward` or an in-cluster `curl` pod. The job fails on any non-200 response.
   6. Run the `@smoke` tag through the Playwright BDD command that `docs/reference/e2e-harness.md` names, with the real SpiceDB and no mock.
2. Smoke scenario (new Gherkin file under the e2e feature directory, tag `@smoke`):
   - Given the ingress is up, when a visitor opens the App Shell, then the sign-in view appears.
   - Given the gateway, when the page loads, then the public readiness route reports every upstream ready.
   The scenario uses UI only. It creates no user.
3. Image push job `push-images` (runs only on `push` to `main`, and only when the registry input is set):
   - Log in to the registry with the secret named in D2b.
   - Run `make images-push` (record 0960).
   - Upload `deployments/helm/runefoble/values.images.yaml` as a workflow artifact. A release commit updates the file.
4. Keep the `e2e-playwright` mock job unchanged. Its purpose is the fast UI loop, and its mock is labelled as such.
5. The `kind-smoke` job uses no repository secret. Only `push-images` reads a registry credential.

Rules for this record:
- A smoke failure fails the job. No retry hides a failed readiness check.
- The job does not depend on a developer machine or on `values.local.yaml`.

### Inputs (user decisions)

- D2: registry host and path (for the push job), and whether `main` pushes images (default: yes, when the registry is set).
- D2b: registry credential name (a GitHub Actions secret) and its scope.

## Frontdoor Blackbox Test Plan

- Workflow shape test, `tests/test_blackbox_ci_workflow.py`: parses `.github/workflows/ci.yml` and checks that `kind-smoke` runs `make images`, runs `helm upgrade --install` with `--wait`, does not pass `values.local.yaml`, and runs the `@smoke` tag. It does not check the YAML formatting.
- Live (the CI run itself): on a pull request, `kind-smoke` passes. The job log shows every `/readyz` probe returns 200.
- Live: a deliberately unreachable upstream (a test branch that sets a wrong service URL) fails the `kind-smoke` job. Record the failing run in the PR.
- Live: `push-images` produces a digest for every image on a push to `main` (only when the registry is set).

## Definition of Done

- The `kind-smoke` job passes on two consecutive runs on `main`.
- `make health-check` passes. `ruff` and the existing CI jobs stay green.
- `docs/reference/e2e-harness.md` lists the `@smoke` tag. `docs/reference/cli-interfaces.md` documents the CI use of `make images`.
- `CHANGELOG.md` `[Unreleased]` entry. Recorded at merge.

## Audit Provenance

- Severity: high (no CI path proves the chart installs).
- Source audits: `.audit/research/r1-hosting.md`, sections 10 and 12 (task 15). Lines were checked against `main` at `33885a70`.
