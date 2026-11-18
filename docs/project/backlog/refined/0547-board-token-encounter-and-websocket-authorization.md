---
id: '0547'
title: Board Token, Encounter, and WebSocket Action Authorization
status: Refined
created: 2026-11-17
dependencies:
- TASK-0546
- TASK-0520
- TASK-0541
- TASK-0542
- TASK-0527
governing_adrs:
- ADR-0001
- ADR-0007
- ADR-0014
governing_prds:
- PRD-0001
- PRD-0005
- PRD-0003
- PRD-0021
governing_stories:
- US-0014
- US-0043
- US-0056
- US-0001
target_release: 0.9.0
---

# TASK-0547: Board Token, Encounter, and WebSocket Action Authorization

## Status
Refined

## Summary
Most mutating board routes have no permission check. Anyone can place, move, or remove a token, cast an area spell, change terrain, import a map, toggle doors, and throw physics objects. The board WebSocket applies moves and spell actions for any client. This task adds one permission per action to each route and to each WebSocket message. It writes the `board_token` tuples that the checks need.

## Problem Statement
- Routes with no check (`w3-authz-coverage.md` table rows 83-122): `services/board_state/src/board_state/routers/tokens.py:20,41,93,100` (place, move, move-by-id, remove), `actions.py:22,77`, `aoe.py:26,54,122`, `physics.py:36,80`, `previews_http.py:19,40`, `vfx.py:39,117,151`, `uvtt_import.py:37,87,110`.
- Probe: anonymous `POST .../tokens/{id}/move` and `.../aoe/place` returned 200 and changed state (`w1-board-state.md` F2).
- `services/board_state/src/board_state/routers/previews_ws.py:92-140` (`/ws/boards/{session_id}`): no auth. Board actions run per message. `_handle_confirm_move` moves tokens with no check (`w1-board-state.md` F2, F12).
- `previews_ws_actions.py` and `previews_ws_spells.py` carry more message handlers. They inherit the same gap.
- `board_token` is defined in the schema (`move = character->edit + campaign->run_session`). No service checks or writes `board_token` tuples.

## Documentation & Architecture Review
- ADR-0001: `board_token.move` for token movement. `board.view` for reading the board.
- ADR-0007: board objects belong to the board context. Token tuples are written by the board context at token placement.
- ADR-0014: the frontdoor tests use HTTP and WebSocket routes only.
- `docs/how-to/interact-with-tactile-board-and-ghost-previews.md` and `docs/how-to/forge-procedural-battlemaps-and-tokens.md` describe these routes. Update the auth text.
- Physics and VFX routes are not in a PRD with an explicit auth rule. Use the rule in step 2 and record it in the how-to.

## Product & User Story References
- US-0014 (board WebSocket sync). US-0043 (tactile board and ghost previews). US-0056 (radial menu and AoE templates). US-0001 (voice board commands). PRD-0021 (tabletop physics).

## Detailed Specification & Implementation Plan
1. Permission table (apply in the router, one call per route):
   - Place a token, remove a token: `board.manage_traps` (DM placement) or `board_token.move` on an owned character token.
   - Move a token (HTTP and WebSocket `confirm_move`): `board_token.move` for the token.
   - AoE evaluate: `board.view`. AoE place and remove: `session.participate`.
   - Spell VFX cast and finish, decal decay: `session.participate` for the caster. Decal decay: `board.manage_traps`.
   - Physics throw and knockback: `board_token.move` for the target token.
   - Actions (`actions.py`): `board_token.move` for movement actions, `session.participate` for others.
   - Terrain configure, UVTT import, door toggle, light placement, board create: `board.manage_traps` for DM content. Door toggle by a player uses `session.participate`.
   - Preview routes: `board.view`.
2. Writes: on token placement, write `board_token:<id>#campaign@campaign:<cid>` and, when the token is a character, `board_token:<id>#character@character:<char_id>`. These are written in the same operation as the token save.
3. WebSocket `/ws/boards/{session_id}`:
   - Connect requires the verified principal (TASK-0520) and `board.view`.
   - Each message type maps to one permission from step 1. A denied message returns a protocol error. It does not close the socket.
   - Replace the broad `except` in the handler with typed errors. An unexpected error closes the socket with 1011 and logs the error (`w1-board-state.md` F12).
4. Confirm that TASK-0527 removed every `x-user-id` read from `dependencies.py`. Do not repeat it here.
5. Delete the local `get_spicedb_client` copy. Use the library factory.

## Frontdoor Blackbox Test Plan
Setup: the campaign, the board, a character, and a token are created through their public routes. The character owner joins with the player role through the role route (TASK-0543).
- Before the fix, anonymous `POST .../tokens/{id}/move` returns 200 and changes the position. After the fix it returns 401.
- A player moves a token owned by another player's character: 403. The owner: 200.
- Anonymous `POST .../aoe/place` returns 401. A spectator gets 403.
- Anonymous `POST .../fog-of-war/reveal` returns 401 (also covered in TASK-0546; this suite checks the rest of the board).
- The WebSocket test: an unauthenticated socket is closed with 1008. A player sends `confirm_move` for another player's token and gets a protocol error. The token does not move.
- Token placement writes the `board_token` tuples. A player who owns the character then moves the token and gets 200. Setup uses the placement route only.

## Definition of Done
1. Frontdoor tests exist in `tests/test_blackbox_board_actions_authz.py` and pass against the live harness.
2. Every route in `services/board_state/src/board_state/routers/` that mutates state has one permission call from step 1. A grep for mutating decorators with no `Depends` or permission call returns nothing.
3. `previews_ws*.py` files check each message type. A test covers one denied and one allowed message per type.
4. Docs listed in the Documentation section are updated.
5. `uv run pytest services/board_state` passes. `uv run ruff check services/board_state` passes.
6. No file in the change exceeds 500 lines. Split `previews_ws_actions.py` or `actions.py` if needed.

## Orchestrator Addenda (2026-11-17, round 2)

Source: `.audit/synth/discovered-round2.md`.

- Re-add the token movement isolation scenario that TASK-0543 removed (player isolation and spectator read-only). Use a public token creation route for setup once one exists.

## Audit Provenance

- Severity: critical
- Source audits: `w1-board-state.md`, `w3-authz-coverage.md`
