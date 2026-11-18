---
id: '0767'
title: Session Lifecycle Routes Check the Caller and Session Permissions
status: Refined
created: 2026-11-17
dependencies:
- TASK-0541
governing_adrs:
- ADR-0001
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: game_session
target_release: 0.9.0
---

# TASK-0767: Session Lifecycle Routes Check the Caller and Session Permissions

## Status
Refined. Found during the authz-int integration (`.audit/work/authz-int.md`, Discovered). Merge after
the authz stack (task/authz-int) is on main.

## Summary
The session lifecycle routes take `player_id` from the request body. They do not compare it with
the verified caller, and they do not check a session permission. Any signed-in user can start a
session, or join, leave or mark readiness for any player.

## Problem Statement
- `services/game_session/src/game_session/routers/session.py`: `start`, `join`, `leave` and
  `lobby/readiness` read `player_id` from the body. No `require_principal` comparison. No SpiceDB
  check.
- `leave` (TASK-0690) activates the player's character stand-in, so a forged leave changes another
  player's game.

## Documentation & Architecture Review
- ADR-0001 and `libs/runefoble_auth/schema/runefoble.zed`: `session.control = campaign->run_session`,
  `session.participate = campaign->play`.
- `docs/how-to/verify-identity-in-fastapi-and-websockets.md`.

## Product & User Story References
None. Security.

## Detailed Specification & Implementation Plan
1. `start`: require `session.control` for the verified caller.
2. `join`, `leave`, `lobby/readiness`: the player is the verified caller. Remove `player_id` from
   the body (no compatibility field, DoR 9), or refuse with 403 when it differs from the caller.
   Prefer removal. Require `session.participate`.
3. A DM action for another player (for example a forced leave) is a separate route that requires
   `session.control`. Add it only if a current caller needs it; record the decision.
4. Update the gateway proxy, the App Shell lobby calls and the MCP tools that call these routes.

## Frontdoor Blackbox Test Plan
- A player with `campaign#player` joins, marks readiness and leaves their own seat: 200.
- The same player tries to leave or mark readiness for another player: 403, no event, no stand-in.
- A user with no campaign relation tries each route: 403.
- A player (not DM) tries `start`: 403. The DM starts: 200.

## Definition of Done
- Every session lifecycle route checks the verified caller and a schema permission.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: high
- Source audits: `work/authz-int.md`
