---
id: '0697'
title: One Shared Service Test Harness Replaces Per-Directory Service Fixtures
status: Refined
created: 2026-11-17
dependencies:
- TASK-0684
governing_adrs:
- ADR-0014
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: core
target_release: 0.9.0
---
# TASK-0697: One Shared Service Test Harness Replaces Per-Directory Service Fixtures

## Status
Refined. Agreed at the refactor pause on 2026-11-17 (candidate 1). The refactor-r1 tests report gives the inventory.

## Summary
Many `tests/**/conftest.py` files start services, set auth verifiers, set SpiceDB clients and set the event bus, each in its own way. This causes order-dependent failures and missing test buses (batches 11 to 13).

## Problem Statement
- Per-directory conftests repeat service start-up, verifier and bus wiring (see the inventory in `.audit/reports/refactor-r1/tests.md`).
- Module globals are set without restore in some fixtures, so later tests see earlier state.
- `tests/conftest.py` keeps several hand-written module lists (`SPICEDB_SERVICE_MODULES`, `REDIS_BUS_MODULES`, `SERVICE_VERIFIER_MODULES`, `SERVICE_IDENTITY_MODULES`).

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0014, ADR-0015.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Add `tests/helpers/service_harness.py`: one declarative registry of services (module, app, auth seam, SpiceDB seam, bus seam), and fixtures that start a service as a live loopback upstream or an in-process client with every seam set and restored.
2. Replace the module lists in `tests/conftest.py` with the registry.
3. Move each per-directory conftest to the harness. Delete the duplicates. Update call sites directly (no aliases).
4. Document the harness in `docs/how-to/test-cross-service-calls-with-live-upstreams.md` (or a new how-to).

## Frontdoor Blackbox Test Plan
- Run the directories that failed by order in batches 11 to 13 together in one run, in two different orders. Assert the same result.
- The full suite with `-p randomly` (if installed) or a reversed file order passes.

## Definition of Done
- No per-directory conftest starts a service or sets a seam by hand.
- One registry lists every service seam.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `work/batch13.gates.log`, `work/fixmain13.md`, `work/0684.md`, `reports/refactor-r1/tests.md`
