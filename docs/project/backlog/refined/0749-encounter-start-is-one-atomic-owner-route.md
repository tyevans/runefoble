---
id: '0749'
title: Encounter Start Is One Atomic Owner Route in game_session
status: Refined
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0007
- ADR-0015
governing_prds:
- PRD-0022
- PRD-0005
governing_stories:
- US-0008
target_bc: game_session
target_release: 0.9.0
---
# TASK-0749: Encounter Start Is One Atomic Owner Route in game_session

## Status
Refined. Found by the refactor audit round refactor-r1 and checked against the code on 2026-11-17.

## Summary
The MCP `create_encounter` tool runs domain orchestration in the gateway: it starts combat, creates the board, and places each token. If placing token N fails, combat is already started and tokens 1 to N-1 remain. No compensation runs.

## Problem Statement
- `gateway/mcp/src/gateway_mcp/tools/board.py:109-147` starts combat in game_session, calls `_fetch_or_create_board` in board_state, then places each enemy token in a loop. The gateway decides grid size (`ENCOUNTER_COLS`, `ENCOUNTER_ROWS`, `:17-18`).
- TASK-0686 (complete) set this design. This task replaces it.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0007, ADR-0015.
- ADR-0015 (b): the gateway is thin. `docs/reference/fastmcp-gateway.md` and `docs/how-to/add-a-watcher-ai-tool.md`. Update the tool description.
- Decision made here: game_session owns the encounter route and calls board_state through the shared service client. Sequence: validate all placements against the board first, then start combat, then place tokens. If a placement fails after combat starts, game_session ends the combat it started and returns one error.

## Product & User Story References
- PRD-0022
- PRD-0005
- US-0008

## Detailed Specification & Implementation Plan
1. Add `POST /api/v1/sessions/{session_id}/encounters` in game_session. It validates, starts combat, calls board_state, and compensates on failure. Grid defaults live in game_session settings.
2. Reduce the MCP tool to one call through the shared client. Delete `_fetch_or_create_board` and the grid constants from the gateway.
3. Record the compensation rule in `docs/reference/ports-and-endpoints.md`.

## Frontdoor Blackbox Test Plan
- Start an encounter with three enemies where the second placement fails (loopback board_state upstream that returns 500 on the second call). Assert one error result and that a later read of combat state shows no started combat.
- Happy path: three enemies placed, combat started, one result.

## Definition of Done
- The MCP tool makes one upstream call. The new route is in the game_session OpenAPI document.
- `uv run pytest`, `make lint`, and `make health-check` pass. No file over 500 lines.
- Docs touched by the change are correct. `CHANGELOG.md` has an `[Unreleased]` entry.

## Audit Provenance
- Severity: medium
- Source audits: `gateway-mcp.md (F5)`
