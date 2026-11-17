---
id: '0686'
title: MCP create_encounter Starts Combat Through Game Session
status: Refined
created: 2026-11-17
dependencies:
- TASK-0671
- TASK-0605
- TASK-0623
governing_adrs:
- ADR-0015
- ADR-0007
governing_prds:
- PRD-0001
governing_stories:
- US-0001
target_release: 0.9.0
severity: high
source_audits:
- work/0671.md
---

# TASK-0686: MCP create_encounter Starts Combat Through Game Session

## Status
Refined. Discovered in round 2 audit of report 0671. Decision by the orchestrator: the encounter key is the game session id. Board-only encounter ids are removed.

## Summary
The MCP tool `create_encounter` creates a board_state board and returns the board id as `encounter_id`. The companion tool `query_encounter_state` reads round and turn order from game_session using the same id. Round trip from create to query fails with a game_session 404. This task makes game_session own the combat lifecycle and makes the session id the encounter id.

## Problem Statement
- `gateway/mcp/src/gateway_mcp/tools/board.py:82-110`: `create_encounter` calls `create_board` and returns `board["session_id"]` as `encounter_id`. It never calls game_session.
- `gateway/mcp/src/gateway_mcp/tools/board.py:64-76`: `query_encounter_state` reads `get_combat_state(encounter_id)` from game_session. The round trip fails.
- `docs/reference/fastmcp-gateway.md` `create_encounter` row describes the limit. It must describe the new contract.

## Documentation & Architecture Review
- ADR-0015 (a): game_session owns session and combat state. The gateway MCP holds no state.
- ADR-0015 (b): on upstream failure the tool returns an error. It does not return a substitute id or canned board.
- `docs/reference/fastmcp-gateway.md`: update the row.

## Product & User Story References
- PRD-0001 and US-0001 (spoken board manipulation). The DM creates an encounter by voice or tool, and the board and the session show the same encounter.

## Detailed Specification & Implementation Plan
1. Change the tool input to `session_id` (an existing game session) plus `enemies`. Remove the board-only path.
2. Call `POST /api/v1/sessions/{session_id}/combat/start` through the shared service client. Build `combatants` from the enemy placements.
3. Create or fetch the board for that session through board_state. If board_state has no fetch-or-create by session id, add one in board_state (one route, one test).
4. Place each enemy token on that board. Mark them not friendly.
5. Return `encounter_id` equal to `session_id`, the board grid, the spawned tokens and the combat state from game_session.
6. `GAME_SESSION_URL` is already read by `gateway_mcp/settings.py`. Its Helm wiring comes from TASK-0623.
7. Update the tool registry test and the reference row.

## Frontdoor Blackbox Test Plan
- Through the public gateway routes, create a campaign and a session, then join one player.
- Call `create_encounter` through the MCP tool with the session id and two enemies.
- Call `query_encounter_state` with the same id. Assert `in_combat` is true, round is 1, and two monster tokens are on the board.
- Call `create_encounter` with an unknown session id. Assert a tool error and no board created.
- Stop game_session (test double returns 503). Assert a tool error, not a board id.

## Definition of Done
- The round trip from `create_encounter` to `query_encounter_state` passes.
- No board-only encounter id remains in code or docs.
- `uv run pytest` and `make lint` pass. Reference doc updated.
