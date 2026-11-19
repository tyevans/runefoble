---
id: '0922'
title: The DM Sets Up the Session Battlemap and Places the Party Tokens
status: Refined
created: 2026-11-19
dependencies:
- '0906'
governing_adrs:
- ADR-0013
- ADR-0014
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: board_state
target_release: 0.9.0
---

# TASK-0922: The DM Sets Up the Session Battlemap and Places the Party Tokens

## Status

Refined. Found by TASK-0652 (`.audit/work/0652.md`).

## Summary

No public product flow creates a session board or places a token. board_state has `POST /api/v1/boards` and a token placement route, but the gateway does not expose them and no UI calls them. A session therefore never has a battlemap, and the VTT scenarios (token kinematics, movement sync) cannot run. The user chose (2026-11-19) that the DM creates the board later through a map flow. TASK-0906 shows "No battlemap yet"; this task adds the flow behind it.

## Problem Statement

- `services/board_state/src/board_state/routers/boards.py:47`: `POST /api/v1/boards` exists. `services/board_state/src/board_state/dependencies.py:58`: boards are created only through it.
- `gateway/api/src/gateway_api/routers/boards_proxy.py`: proxies read, token read and token move only. No create route and no token place route.
- `e2e/features/session_lobby_and_vtt.feature` scenarios 3 and 4 need a board with party tokens.

## Documentation & Architecture Review

- Gateway rule (TASK-0845): a proxy route forwards the token, and the owner checks the permission (`campaign.run_session` or the board create permission in `runefoble.zed`).
- `docs/how-to/interact-with-tactile-board-and-ghost-previews.md`, `docs/how-to/forge-procedural-battlemaps-and-tokens.md`.

## Product & User Story References

- The VTT scenarios in `e2e/features/session_lobby_and_vtt.feature`.

## Detailed Specification & Implementation Plan

1. Gateway: proxy `POST /api/v1/boards` and the token place route to board_state (forward the token; the owner checks).
2. UI: the DM sees "Set up battlemap" in the `<runefoble-board-empty>` state (TASK-0906). It creates the board with a default grid size (or a forged map if one is selected), then places one token for each seated character at free start cells. A player sees no set-up control.
3. The view then loads the board and shows the tokens. A failed call shows the owner's error and creates nothing on the client side.
4. Docs: the how-to and the ports-and-endpoints reference.

## Frontdoor Blackbox Test Plan

- Gateway blackbox: the DM creates a board and places a token through the gateway, then reads them back. A player gets the owner's 403. Unreachable owner gives 503.
- Playwright on Kind (orchestrator): `session_lobby_and_vtt.feature` scenarios 3 and 4, with the board set up through the new UI control.

## Definition of Done

- Tests above pass. Docs and CHANGELOG `Added` entry.

## Audit Provenance

- Severity: high
- Source audits: .audit/work/0652.md
