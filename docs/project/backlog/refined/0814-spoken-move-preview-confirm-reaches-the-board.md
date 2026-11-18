---
id: '0814'
title: "A Spoken Move Reaches the Board Through Preview and Player Confirm"
status: Refined
created: 2026-11-18
dependencies:
- TASK-0583
governing_adrs:
- ADR-0014
- ADR-0015
governing_prds:
- PRD-0001
governing_stories: []
target_bc: board_state
target_release: 0.9.0
---

# TASK-0814: A Spoken Move Reaches the Board Through Preview and Player Confirm

## Status
Refined

## Summary
No test shows that a spoken move reaches the board. The design is: The Watcher proposes (a ghost preview), and the player confirms. Only the confirm commits the move.

## Problem Statement
- TASK-0583 proxies speak-and-act to The Watcher. The move publishes `runefoble.events.board.token_moved`, but `board_state` does not apply that event, by design.
- `services/board_state/src/board_state/routers/previews_ws.py` handles `speech_intent_parsed` previews and `confirm_move`. No test covers the chain from speech to the committed position.

## Documentation & Architecture Review
- `docs/explanation/the-watcher-autonomous-dm.md` (assistant, never a dictator), `docs/how-to/interact-with-tactile-board-and-ghost-previews.md`.

## Product & User Story References
PRD-0001.

## Detailed Specification & Implementation Plan
1. Confirm which component sends the preview to the board socket after speak-and-act, and wire it if no component does.
2. Add one frontdoor test: speak-and-act through the gateway, the board socket receives the preview, the player sends `confirm_move`, and `GET /api/v1/boards/{id}` shows the new position.
3. Delete the `token_moved` board publish if nothing consumes it (TASK-0703 rule).

## Frontdoor Blackbox Test Plan
- The chain test in step 2.
- Without confirm, the position does not change.

## Definition of Done
- The test plan passes. `make test`, `make lint` and `make health-check` pass.

## Audit Provenance
- Severity: medium
- Source audits: `.audit/work/0583.md` (Blocker, option A chosen by the orchestrator)
