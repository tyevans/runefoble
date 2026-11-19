---
id: '0932'
title: The Board Drag Sends One Move and Shows Refusals
status: Refined
created: 2026-11-19
dependencies:
- '0928'
governing_adrs:
- ADR-0004
- ADR-0014
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: board_state
target_release: 0.9.0
---

# TASK-0932: The Board Drag Sends One Move and Shows Refusals

## Status

Refined. Found by the fifth full e2e run on Kind (`.audit/work/vtt-drag.md`).

## Summary

The "Live Token Kinematics and Movement Sync" scenario failed. The e2e drag step pressed the mouse at a point outside the viewport, because the board was below the fold and a raw mouse drag does not scroll. Two product defects were also found: the click that ends a drag sent a second `confirm_move` back to the start cell, and the board element ignored server error frames, so a refused move showed nothing. board_state also dropped a move with no target cell without any frame.

## Problem Statement

- `e2e/steps/battlemap_setup_steps.ts:62-82`: raw `mouse.move/down/up` with no scroll into view.
- `services/board_state/ui/src/runefoble-board.ts`: `handlePointerUp` then `handleCellClick` both sent a move.
- The board socket message handler dropped `error` frames.

## Documentation & Architecture Review

- `docs/how-to/interact-with-tactile-board-and-ghost-previews.md`.

## Product & User Story References

- `e2e/features/session_lobby_and_vtt.feature` scenario 4.

## Detailed Specification & Implementation Plan

1. The e2e step scrolls the token and the target cell into view before the drag.
2. A drag sends exactly one `confirm_move`.
3. The board shows a refusal from the server in an alert line. Error frames name `action` and `token_id`.
4. board_state answers a move with no target cell with an error frame.
5. The board socket `connected` frame carries the current tokens, and `<runefoble-board>` applies them, so a socket that opens after a move shows the current board. The App Shell mounts no board element (and opens no board socket) until the board read answers, and a reload uses the server cells (`.audit/work/vtt-sync.md`).

## Frontdoor Blackbox Test Plan

- Pytest: a move with no target cell gets an error frame.
- Chromium DOM test: one drag sends one `confirm_move`; an error frame shows the alert line.
- Playwright on Kind (orchestrator): scenario 4.

## Definition of Done

- Tests pass. CHANGELOG `Fixed` entry.

## Audit Provenance

- Severity: medium
- Source audits: .audit/work/vtt-drag.md
