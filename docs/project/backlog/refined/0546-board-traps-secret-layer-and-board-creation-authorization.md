---
id: '0546'
title: Board Traps, Secret Layer, and Board Creation Authorization
status: Refined
created: 2026-11-17
dependencies:
- TASK-0520
- TASK-0541
- TASK-0542
- TASK-0540
- TASK-0527
governing_adrs:
- ADR-0001
- ADR-0007
- ADR-0014
governing_prds:
- PRD-0003
- PRD-0001
governing_stories:
- US-0018
- US-0012
target_release: 0.9.0
severity: critical
source_audits:
- w1-board-state.md
- w3-authz-coverage.md
---

# TASK-0546: Board Traps, Secret Layer, and Board Creation Authorization

## Status
Refined

## Summary
The board service returns secret traps to anonymous callers. Anonymous callers can disarm traps and switch maps. The trap permission helper uses names that are not in the schema, and it hides every error in `except Exception: pass`. No code writes board tuples, so the board branch of the check never matches. This task makes the secret layer a schema permission, redacts secret data for callers who do not hold it, fixes the trap and map-switch checks, and writes the board tuples at creation.

## Problem Statement
- `services/board_state/src/board_state/routers/boards.py` (`GET /api/v1/boards/{session_id}`) returns the raw `BoardState`. Secret traps include `is_secret`, `description`, `effect_payload`, and `dc_detection` (`models/board.py:40`). Probe: anonymous GET returns the secret trap id and its DM description (`w1-board-state.md` F1).
- `services/board_state/src/board_state/routers/traps.py:129` (`POST .../traps/{trap_id}/disarm`): no check. The identity is an optional header. Probe: anonymous disarm returns 200 (`w1-board-state.md` F2).
- `services/board_state/src/board_state/dependencies.py` (`check_user_can_manage_traps`): calls `campaign.dungeon_master`, `campaign.owner`, `board.dungeon_master`, `session.run_session`, and `game_session.run_session`. Each call is inside `except Exception: pass`. When `campaign_id` is missing the check uses `campaign:<board_id>` (`w1-board-state.md` F8).
- No code writes `board:` tuples (`w1-board-state.md` F8). The board branch is dead.
- `services/board_state/src/board_state/routers/terrain.py:19` (`GET .../visibility?is_dm=`) lets any caller claim DM. Lines 67-88 (`fog-of-war/reveal` and `/shroud`) have no check and return hidden tokens with `is_dm=True` (`w3-authz-coverage.md` F12).
- `services/board_state/src/board_state/routers/boards.py:59` (`POST /api/v1/boards`): no check (`w3-authz-coverage.md` route 89).
- `services/board_state/src/board_state/dependencies.py:get_current_user_id` reads `x-user-id` (`w1-board-state.md` F15). Identity is TASK-0520. This task consumes the verified principal.

## Documentation & Architecture Review
- ADR-0001: `board.manage_traps`, `board.view_secret_layer`, and `board.switch_map` are the schema permissions for this context. `board.dungeon_master` is a relation that the `campaign` branch covers, so the check does not name it.
- ADR-0007: the board context owns board objects. Board tuples are written by the board context at creation (`board:<id>#campaign@campaign:<cid>`).
- `docs/how-to/manage-secret-dm-traps-and-map-triggers.md` uses the `x-user-id` header in its examples. Replace the examples with the verified principal.
- `docs/reference/ports-and-endpoints.md` lists the board routes. Update the auth column.

## Product & User Story References
- US-0018 (secret DM traps, map switching, stage triggers).
- US-0012 (spatial line of sight and fog of war).
- PRD-0003 (visibility engine: hidden tokens must not reach non-DM callers).

## Detailed Specification & Implementation Plan
1. `dependencies.py`. The principal comes from TASK-0527. This task does not change identity:
   - Replace `check_user_can_manage_traps` with one function per action. `require_board_permission(board_id, permission)` calls `check_permission("board", board_id, permission, "user", principal)`.
   - Remove every `except Exception: pass`. An `AuthzUnavailableError` returns 503. An `AuthzSchemaError` returns 500 with an error id, and it is logged.
   - Delete the `campaign:<board_id>` fallback. A missing campaign on board creation returns 400.
   - Delete the local copy of `get_spicedb_client` and import the library factory (TASK-0541).
2. Board creation (`boards.py:59`): require the verified principal and `campaign.run_session` on the campaign in the body. After the board is saved, write `board:<id>#campaign@campaign:<cid>` through the library.
3. Secret layer read (`boards.py`, `GET /api/v1/boards/{session_id}`): remove secret trap fields for a caller without `board.view_secret_layer`. The public projection keeps the trap id only when the trap is revealed. Redaction is done in the projection, not in the router.
4. Traps (`traps.py`):
   - `POST .../traps` (create), `GET .../traps` (secret filter), `DELETE` and `disarm`: require `board.manage_traps`. Before writing this step, read the trap model in `services/board_state/src/board_state/models/` and decide whether players may disarm a non-secret trap. If the model has no such field, DM only is the rule. Write the rule in the route docstring.
   - `POST .../switch-map`: require `board.switch_map`.
5. Terrain (`terrain.py`):
   - `GET .../visibility`: remove the `is_dm` query parameter. Compute the DM flag with `board.view_secret_layer`.
   - `POST .../fog-of-war/reveal` and `/shroud`: require `board.view_secret_layer`.
   - `POST .../terrain`: require `board.manage_traps`.
6. Do not change token, action, AoE, physics, or WebSocket routes here. They belong to TASK-0547.

## Frontdoor Blackbox Test Plan
Setup: the campaign is created through its public route. The DM joins with the DM role through the role route (TASK-0543). A board is created through `POST /api/v1/boards`. The secret trap is created through the trap route.
- Before the fix, anonymous `GET /api/v1/boards/{session_id}` returns the secret trap id. After the fix it does not, for an anonymous caller and for a player.
- The DM gets the secret trap in the same GET.
- Anonymous `POST .../traps/{id}/disarm` returns 401. A player on a secret trap gets 403. Before the fix it returns 200.
- Anonymous `POST .../switch-map` returns 401. A player gets 403. The DM gets 200.
- `GET .../visibility?is_dm=true` from a player does not return hidden tokens.
- Board creation with a campaign the caller does not manage returns 403. Board creation with no campaign returns 400.
- A schema or transport error from a stubbed SpiceDB returns 503 or 500, not 200 or 403.

## Definition of Done
1. Frontdoor tests exist in `tests/test_blackbox_board_traps_authz.py` and pass against the live harness.
2. No `except Exception: pass` or `contextlib.suppress(Exception)` wraps a permission check in `services/board_state/`.
3. `grep -rn "dungeon_master\|game_session" services/board_state/src` returns no permission call.
4. `docs/how-to/manage-secret-dm-traps-and-map-triggers.md` and `docs/reference/ports-and-endpoints.md` match the code.
5. `uv run pytest services/board_state` passes. `uv run ruff check services/board_state` passes.
6. No file in the change exceeds 500 lines.
