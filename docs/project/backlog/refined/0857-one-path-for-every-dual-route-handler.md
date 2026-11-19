---
id: '0857'
title: Each Route Serves One Path, With an Inventory Test That Keeps It So
status: Refined
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0011
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: platform
target_release: 0.9.0
---
# TASK-0857: Each Route Serves One Path, With an Inventory Test That Keeps It So

## Status
Refined

## Summary
Forty-nine handlers in thirteen router files carry two route decorators: a bare path and an `/api/v1` path. Both paths are live. Two `game_session` routers are also included twice, once with and once without the `/api/v1` prefix. DoR 9 forbids aliases. This task keeps the `/api/v1` path, removes the bare path and the extra include, and adds an inventory test. The test fails when any operation has two paths.

## Problem Statement
- AST scan of `services/*/src` (excluding `ui/` and `audience_studio`) finds 49 handlers with both a bare and an `/api/v1` decorator:
  - `game_session` (8 settlement files and 1 root file, 36 handlers): `settlement/bulletin_router.py` (4), `settlement/haggling_router.py` (6), `settlement/haven/routes_establishments.py` (3), `settlement/haven/routes_havens.py` (3), `settlement/haven/routes_upgrades.py` (2), `settlement/workers/routes_inventory.py` (4), `settlement/workers/routes_relationships.py` (4), `settlement/workers/routes_roster.py` (5), `routers/reactions.py` (5).
  - `board_state`: `routers/traps.py` (4), `routers/uvtt_import.py` (3).
  - `the_watcher`: `routers/faction_resources.py` (4), `routers/turf_war.py` (2).
- Include-level aliases in `services/game_session/src/game_session/main.py`: `settlements_router` at lines 105 and 106, and `bounties_router` at lines 110 and 111. Each router is included once with no prefix and once with `prefix="/api/v1"`. Both paths are live.
- Example: `services/game_session/src/game_session/routers/reactions.py:149-150` decorates the same handler with `@router.get("/sessions/{session_id}/reactions/active")` and `@router.get("/api/v1/sessions/{session_id}/reactions/active")`.
- Note: the earlier grep count in the input reports (69 handlers in about 25 files) is not reproduced by the AST scan. The index records the difference.

## Documentation & Architecture Review
- DoR 9: no backward-compatibility aliases.
- ADR-0015 (b): one path per operation through the gateway.
- `docs/reference/ports-and-endpoints.md` and `docs/reference/game-session-child-indexes.md`: update the path lists.
- TASK-0751 and TASK-0752 (refined) edit some of the same `board_state` routers. TASK-0858 edits some of the settlement routers. Coordinate the merge order.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Grep each bare path (`services/`, `gateway/`, `libs/`, `tests/`, `frontend/src/`, `docs/`) before you delete it. Keep a list of callers. Update each caller to the `/api/v1` path in the same change.
2. For each handler in the thirteen files, delete the bare decorator. Keep the `/api/v1` decorator. Do not change the handler body.
3. In `game_session/src/game_session/main.py`, delete the un-prefixed includes at lines 105 and 110. Keep the `prefix="/api/v1"` includes at lines 106 and 111.
4. For each router that now carries `/api/v1` decorators and an include prefix, check that the path does not start with `/api/v1` twice. Fix the case if found.
5. Add `tests/test_route_single_path.py`. For each service, read `/openapi.json` from the service test client. Assert that no operation (method and handler) appears under two paths. Use only the public OpenAPI document. Do not import route modules.
6. Update tests and docs that call a bare path. `tests/test_blackbox_downtime_contracts_authz.py:38`, `:48`, and `:56` are known callers.

## Frontdoor Blackbox Test Plan
- For each service, `/openapi.json` lists each operation once. The inventory test asserts this.
- Sample operations in each changed router answer on the `/api/v1` path. The bare path answers 404.
- Existing gateway proxy tests for these routes pass unchanged.

## Definition of Done
- No route decorator without `/api/v1` remains in the thirteen files.
- The two unprefixed includes are removed from `game_session/main.py`.
- The inventory test passes for every service.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `refactor-r2/services-backend.md` (F1), corrected by the AST scan in the backend index
