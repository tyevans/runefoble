---
id: '0548'
title: Game Session Lifecycle, Combat, Hot-Swap, and Minigame Socket Authorization
status: Refined
created: 2026-11-17
dependencies:
- TASK-0520
- TASK-0541
- TASK-0542
- TASK-0540
- TASK-0529
- TASK-0522
governing_adrs:
- ADR-0001
- ADR-0007
- ADR-0011
- ADR-0014
governing_prds:
- PRD-0001
- PRD-0002
governing_stories:
- US-0026
- US-0065
- US-0023
- US-0007
target_release: 0.9.0
---

# TASK-0548: Game Session Lifecycle, Combat, Hot-Swap, and Minigame Socket Authorization

## Status
Refined

## Summary
Session creation, start, join, leave, turn advance, dice rolls, combat, reactions, and autopilot have no object check. No session tuple is written, so no check could pass for a game session. Hot-swap runs its check only when a header is present, and it checks the `game_session` type that nothing writes. The minigame sockets take the player id from the message and skip checks for the default establishment. This task binds each lifecycle route to the `session` object, writes the session tuples in one place, and makes every check fail closed.

## Problem Statement
- `services/game_session/src/game_session/routers/session.py` routes `create` (line 36), `start` (56), `join` (80), `leave` (97), `next-turn` (173), and `roll` (185) contain no check (`w1-game-session.md` F8).
- Nothing writes `game_session` or `session` tuples on creation. `libs/runefoble_auth/schema/runefoble.zed:35-41` defines `game_session#campaign`, but nothing writes it. The gateway writes `session#campaign` (`gateway/api/src/gateway_api/routers/campaigns.py:55`).
- `routers/session.py:116` (hot-swap): the check runs only `if x_user_id:`. A request with no header goes straight to the hand-off. Line 126 checks `game_session`, which is never written, so the fallback always denies (`w1-game-session.md` F7).
- `routers/autopilot.py:32`, `routers/combat.py:60,93,132,166`, `routers/reactions.py:44,69,99,126`: no check (`w3-authz-coverage.md` rows 163-189).
- `routers/minigames_ws.py:31`: the player check runs only when `user_id` is present and the establishment is not `est-default`. Lines 64 and 73 take `player_id` from the message payload, so any client acts as any player. `gateway/api/src/gateway_api/main.py:134,146` always uses `est-default` (`w3-authz-coverage.md` F14).
- `services/game_session/src/game_session/minigame_tables/actions.py:186`: the roulette result is client-supplied. This is a fake-implementation issue, recorded in the index. This task removes only the authority the client has over identity.

## Documentation & Architecture Review
- ADR-0001: the `session` type is the lifecycle object. `session.control` for DM actions, `session.participate` for player actions, `session.observe` for read-only views. `game_session` is not used in this task. TASK-0559 removes its definition after no check uses it.
- ADR-0011: lifecycle transitions remain on the aggregate. This task does not move state out of the aggregate. Permission checks happen before the command.
- ADR-0007: session tuples are written by the session context at creation, and by the campaign context on campaign join.
- `docs/how-to/coordinate-game-session-lobby-and-readiness.md` and `docs/how-to/configure-stand-in-guardrails-and-hot-swap.md` describe these routes. Update the auth text.
- Tuples from the bus listener (`libs/runefoble_auth/src/runefoble_auth/listener.py:61`, never registered, `w3-event-wiring.md` F5) are not used. Writes happen in the route, through the library.

## Product & User Story References
- US-0026 (mid-session hot-swap, permadeath lock). US-0065 (lobby, readiness, launch). US-0023 (reaction interrupts). US-0007 (autonomous DM execution). PRD-0002 (stand-in).

## Detailed Specification & Implementation Plan
1. Session creation (`session.py:36`): require the verified principal and `campaign.run_session` on the campaign in the body. After the save, write `session:<id>#campaign@campaign:<cid>`.
2. Permission per route:
   - `start`, `next-turn`, `roll` (DM roll) and combat start, initiative, next-turn, end: `session.control`.
   - `join`, `leave`: `session.participate`. Join writes `session:<id>#participant@user:<principal>`. Leave deletes it. A write error returns 503.
   - Dice roll by a player: `session.participate`.
   - Reactions declare, resolve, and ready-action: `session.participate` for the reacting character. Evaluate-triggers: `session.control`.
   - Autopilot: `session.control`.
3. Hot-swap (`session.py:109-130`):
   - Principal from TASK-0529. Missing principal returns 401 (from that task).
   - Check `session.participate` for the requesting player and `character.edit` for the character being handed off.
   - Remove the `game_session` check.
   - The hand-off must match the player and the character in the request. Lines that accept a mismatched pair are removed (`w1-game-session.md` F18).
4. Minigame sockets (`minigames_ws.py`):
   - Connect uses the principal from TASK-0529 (service) and TASK-0522 (gateway). `player_id` comes from the principal.
   - Remove the `est-default` bypass. The socket checks `session.participate` (or `session.observe` for spectators) on the session that the table belongs to.
   - The gateway socket routes (`main.py:134,146`): this task removes the `est-default` bypass. Removing the `user_id` query parameter is TASK-0522.
5. Delete the local `get_spicedb_client` copy and use the library factory. Use `ACTION_PERMISSIONS` only.

## Frontdoor Blackbox Test Plan
Setup: the campaign, the session, and characters are created through public routes. Players join through invites. The DM uses the role route to get `dungeon_master`.
- Before the fix, anonymous `POST /api/v1/sessions/{id}/start` returns 200. After the fix it returns 401.
- A player calls `POST .../start`: 403. The DM: 200.
- A player calls `POST .../combat/start`: 403. Before the fix it returns 200.
- Creating a session writes the session tuple. A player who is a member of the campaign then calls `POST .../join` and gets 200. A non-member gets 403.
- Hot-swap with no `x-user-id` and no token: 401. Hot-swap with a mismatched character: 403.
- A minigame socket with a `player_id` in the payload that is not the principal: the server ignores the payload id and uses the principal. A spectator cannot send actions.

## Definition of Done
1. Frontdoor tests exist in `tests/test_blackbox_session_lifecycle_authz.py` and pass against the live harness.
2. No `if x_user_id` or `if user_id` gate remains in `services/game_session/src/game_session/routers/session.py`, `combat.py`, `reactions.py`, `autopilot.py`, or `minigames_ws.py`.
3. `grep -rn "game_session" services/game_session/src/game_session/routers` returns no permission call.
4. `docs/how-to/coordinate-game-session-lobby-and-readiness.md` and `docs/how-to/configure-stand-in-guardrails-and-hot-swap.md` are updated.
5. `uv run pytest services/game_session` passes. `uv run ruff check services/game_session` passes.
6. No file in the change exceeds 500 lines. `session.py` is already large; split it if this change pushes it over.

## Audit Provenance

- Severity: critical
- Source audits: `w1-game-session.md`, `w3-authz-coverage.md`
