---
id: '0721'
title: Auth Lib Holds Only Identity Code
status: Complete
created: 2026-11-17
dependencies:
- TASK-0486
governing_adrs:
- ADR-0001
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: core
target_release: 0.9.0
---
# TASK-0721: Auth Lib Holds Only Identity Code

## Status
Complete

## Summary
The auth lib ships Zitadel bootstrap tooling and a test double. It also builds concrete adapters when none is injected.

## Problem Statement
- `libs/runefoble_auth/src/runefoble_auth/zitadel_bootstrap.py` (removed), moved to `deployments/zitadel_bootstrap/src/zitadel_bootstrap/`, (181 lines) and `zitadel_bootstrap_job.py` (163 lines) are deployment tooling. `deployments/helm/runefoble/templates/zitadel-bootstrap.yaml:82` runs `python -m runefoble_auth.zitadel_bootstrap_job`.
- `libs/runefoble_auth/src/runefoble_auth/testing/signing_test_issuer.py` (removed), moved to `tests/helpers/signing_test_issuer.py`, (112 lines) is a test double in the production package. About eight test modules import it.
- `libs/runefoble_auth/src/runefoble_auth/sync.py:41-42`: `spicedb_client or SpiceDBClient()` and `zitadel_auth or ZitadelAuthService()`. The `or` tests truthiness, not `None`.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0001, ADR-0015.
- `docs/how-to/` and `docs/reference/` pages named in the specification.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Move the bootstrap modules to a deployment job package (for example `deployments/zitadel_bootstrap/`) and update the Helm command and `tests/test_blackbox_zitadel_bootstrap.py`.
2. Move `signing_test_issuer.py` to `tests/helpers/`. Update the test imports.
3. Make `ZitadelSpiceDBSyncService` require both adapters. Call sites pass them.
4. Do not touch the claim sync modules. TASK-0534 is named in ADR-0015 but not found in the backlog; the orchestrator must confirm its scope.

Refactor round 2 addendum (2026-11-18): Decision needed before TASK-0855: step 4 says do not touch the claim sync modules. TASK-0534 is complete, but its step 2 (delete the claim-to-relation mapping in `sync.py`) is still in the code. The orchestrator must confirm the scope of TASK-0855.

## Frontdoor Blackbox Test Plan
- `tests/test_blackbox_zitadel_bootstrap.py` passes with the moved job. `helm template` renders the new command.
- Constructing the sync service with no adapters raises `TypeError`.

## Definition of Done
- The specification steps are done and the tests above pass.
- Docs named in the specification are corrected.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: low
- Source audits: `refactor-r1/libs.md`
