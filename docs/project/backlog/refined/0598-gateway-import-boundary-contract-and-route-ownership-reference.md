---
id: '0598'
title: Gateway Import Boundary Contract and Route Ownership Reference
status: Refined
created: 2026-11-17
dependencies:
- TASK-0589
- TASK-0591
- TASK-0592
- TASK-0593
- TASK-0599
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0010
governing_prds:
- PRD-0023
governing_stories:
- US-0013
target_release: 0.9.0
---

# TASK-0598: Gateway Import Boundary Contract and Route Ownership Reference

## Status
Refined

## Summary
After the proxy tasks merge, `gateway/api` must import only `libs/*` and its own package. Enforce that with an import-linter contract in the uv workspace, so the rule holds in CI. Add one reference table that names the owning bounded context for every public gateway route. Update the architecture overview to match.

## Problem Statement
- Before the proxy tasks, 16 import lines in `gateway/api` reached into service packages (`w3-ddd-architecture.md` Deliverable 2). No check stops a new one.
- `docs/reference/architecture-overview.md:37-47` says the gateway does "OpenAPI spec aggregation" and "WebSocket fanout". It does not say the gateway owns no domain state.
- `docs/reference/ports-and-endpoints.md` lists gateway routes with no owner column. A reader cannot tell which routes proxy and which are local (`w1-gateway-api.md` F17).
- ADR-0003 and the rest of the workspace do not run import-linter today. Check `uv.lock` before adding it.

## Documentation & Architecture Review
- ADR-0003: each package keeps its own `pyproject.toml`. The contract lives in the root `pyproject.toml`.
- ADR-0007: bounded contexts do not reach into each other. This task makes that rule checkable for the gateway. Service-to-service imports are a separate follow-up (see the index report).
- ADR-0010: CI runs the root `uv run pytest`. Put the contract check in a test (`tests/test_import_boundaries.py`) so it runs in the same job, or in a `make lint` step. Choose one and state it in the PR.

## Product & User Story References
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`us-0013-gateway-zanzibar-authorization.md`](../../user_stories/accepted/us-0013-gateway-zanzibar-authorization.md)

## Detailed Specification & Implementation Plan
1. Add `import-linter` as a dev dependency with `uv add --dev import-linter` at the root. Commit the updated `uv.lock`.
2. Add a `[tool.importlinter]` section to the root `pyproject.toml` with one contract:
   - Type: forbidden.
   - Source: `gateway_api`.
   - Forbidden: `the_watcher`, `game_session`, `board_state`, `character_sheet`, `voice_agent`, `campaign_lore`, `campaign_analytics`, `rules_compendium`, `asset_forge`, `soundscape`, `audience_studio`, `inference_worker`.
   - No `ignore_imports` entries are allowed. A violation must be fixed.
3. Run `uv run lint-imports`. Fix any remaining gateway violation in the owning task. Do not add an exception.
4. Add `tests/test_import_boundaries.py`, which runs the same contract through the import-linter API and fails on any violation.
5. Create `docs/reference/gateway-route-ownership.md`. One table: public method and path, owner BC, mode (`proxy`, `relay` for WebSocket, or `local` for gateway-only routes such as health and the campaign WebSocket). Fill every row from the routes the gateway mounts after the proxy tasks.
6. Update `docs/reference/architecture-overview.md` (gateway row) to say the gateway owns auth, routing, WebSocket fan-out and OpenAPI aggregation, and owns no domain state.
7. Update `docs/reference/ports-and-endpoints.md` to link to the ownership table.

## Frontdoor Blackbox Test Plan
- `tests/test_import_boundaries.py`: the import contract on `gateway/api`. Before the proxy tasks it fails with the listed violations. After them it passes.
- `tests/test_gateway_route_ownership_doc.py`: parses `docs/reference/gateway-route-ownership.md` and compares its rows to the routes in the running gateway app (`app.routes`, public methods and paths). It fails on any mounted public route with no row, or any row with no mounted route. This test uses the public app object only.

| Case | Expected before fix | Expected after fix |
|---|---|---|
| Import contract on `gateway/api` | Fails: 16 lines | Passes |
| Ownership table matches mounted routes | Fails: no table | Passes |
| Adding a service import to `gateway/api` in a test copy | Not checked | Fails as designed |

## Definition of Done
1. `uv run lint-imports` exits 0 with the gateway contract and no exceptions.
2. `tests/test_import_boundaries.py` and `tests/test_gateway_route_ownership_doc.py` pass.
3. `docs/reference/gateway-route-ownership.md` exists and matches the routes.
4. `docs/reference/architecture-overview.md` and `docs/reference/ports-and-endpoints.md` are updated.
5. `uv run ruff check .` passes. `uv run pytest` passes.

## Audit Provenance

- Severity: medium
- Source audits: `w3-ddd-architecture.md`, `w1-gateway-api.md`, `w3-docs-integrity.md`
