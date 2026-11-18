---
id: '0657'
title: Tutorial 01 and README Quick Start Produce a Running Local Stack
status: Refined
created: 2026-11-17
dependencies:
- TASK-0620
governing_adrs:
- ADR-0003
- ADR-0005
governing_prds: []
governing_stories:
- US-0004
target_release: 0.9.0
---

# TASK-0657: Tutorial 01 and README Quick Start Produce a Running Local Stack

## Status
Refined

## Summary
Tutorial 01 and the README Quick Start cannot produce a running stack as written. Step 3 deploys images that no step builds. Step 4 opens a Grafana URL that has no route. The prerequisites omit `kubectl`. The SpiceDB port-forward is not described. The Vite proxy list is incomplete. Make every step executable, in the order it must run, and name the Make target that builds and loads images (provided by TASK-0620).

## Problem Statement
- `README.md:26-29` (`make cluster-up`, `make helm-deploy`): no image build or load step. Only `frontend/Dockerfile` exists. `deployments/helm/runefoble/values.yaml` names images such as `runefoble/gateway-api:0.1.0`.
- `docs/tutorials/01-local-development-setup.md:39` (`make helm-deploy`): the same missing build. After deploy, `http://localhost/` has no frontend pod (step 4).
- `docs/tutorials/01-local-development-setup.md:48` gives `http://localhost:3001` for Grafana. `values.yaml` has no Grafana ingress path. `deployments/kind/cluster-config.yaml` maps only ports 80, 443, and 50051. No port-forward step is present.
- Prerequisites (lines 6-13) omit `kubectl`. `make cluster-up`, `make helm-deploy`, and `scripts/dev_server.py:49-97` call it. `make dev` starts `kubectl port-forward svc/spicedb 50051:50051` when SpiceDB is unreachable. Step 5 (line 55) does not mention this.
- Line 55 lists 7 proxied paths. `frontend/vite.config.ts` also proxies `/auth`, `/mailpit`, `/redoc`, `/campaigns`, and `/healthz`.
- The Makefile `cluster-up` target ends the Traefik lines with `2>/dev/null || true` (`Makefile:73-76`). Failures are silent. The tutorial says Traefik is installed.

## Documentation & Architecture Review
- `docs/project/adrs/accepted/adr-0005-kubernetes-first-infrastructure-with-helm-and-kind.md` is the governing ADR for Kind and Helm.
- `docs/reference/cli-interfaces.md` lists Make targets. Add the image target there (in TASK-0663 or this task, whichever lands first; record the choice).
- DoD 4 of `docs/project/backlog/README.md`: docs match code. This task is a documentation correction.

## Product & User Story References
Developer onboarding. US-0004 (developer tests in Storybook) is the closest story. No product PRD applies.

## Detailed Specification & Implementation Plan
1. Use the image build and Kind load target from TASK-0620 in step 3, before `make helm-deploy`. Name the exact target.
2. Add `kubectl` to the prerequisites with a version check command.
3. Grafana: either add a `kubectl port-forward svc/grafana 3001:3001` step (preferred for a tutorial), or the ingress route, with the choice recorded. The doc must state which URL works after the step.
4. Step 5: describe the SpiceDB port-forward that `make dev` starts, and when to run it by hand.
5. Replace the Vite proxy list with the full list, or a link to `docs/reference/ports-and-endpoints.md`.
6. Traefik: state how to check the install (`kubectl -n traefik get pods` or the equivalent in the chart), and note that `make cluster-up` hides failures until the Makefile is fixed. Do not change the Makefile in this task.
7. Each step ends with an expected observable result (a `curl` status code or a page title).

## Frontdoor Blackbox Test Plan
Tutorial verification is a script, not prose review:
- A shell script (`scripts/verify_tutorial_01.sh`, run manually in a local Kind environment, not in CI) runs each tutorial command in order and checks the observable result: `curl -fsS http://localhost/api/v1/health` returns 200, `curl -fsS http://localhost/` returns HTML, and the Grafana step returns 200 on the documented URL.
- Before the fix the script fails at step 3 (no image build). After the fix it passes.

## Definition of Done
1. Following tutorial 01 from a clean machine reaches a 200 response on `http://localhost/api/v1/health`.
2. The README Quick Start links to the same steps and does not repeat wrong ones.
3. Prerequisites include `kubectl`. The Grafana URL works as written.
4. The Vite proxy list matches `frontend/vite.config.ts`.
5. The verification script exists, and its run result is recorded in the task file.
6. Files changed stay under 500 lines.

## Audit Provenance

- Severity: high
- Source audits: `w3-docs-integrity.md`
