---
id: '0938'
title: The Mover's Board Shows Its Own Accepted Token Move
status: Complete
created: 2026-11-19
dependencies:
- '0932'
governing_adrs:
- ADR-0013
- ADR-0014
- ADR-0015
governing_prds:
- prd-0005-realtime-websocket-board-sync
governing_stories:
- us-0065-game-session-lobby-readiness-and-launch
target_bc: board_state
target_release: 0.9.0
---

# TASK-0938: The Mover's Board Shows Its Own Accepted Token Move

## Status

Complete

## Summary

On Kind, the e2e scenario "Live Token Kinematics and Movement Sync" fails 10 of 12 times when it runs alone (`--repeat-each=12`). In the full suite it fails about once in two runs. Board-state accepts the move: the chronicle on the mover's own screen shows "Valeros the Bold moved to (3, 3)". But the board on that screen keeps the token at (0, 0). In one repeat the mover's board was correct and the other player's board did not move.

## Problem Statement

- Evidence: `.audit/work/vtt-repeat/repeat3-error-context.md` (page snapshot), `.audit/work/vtt-repeat/repeat3.webm`, `.audit/work/vtt-repeat/run.log`.
- Step: `e2e/steps/battlemap_setup_steps.ts:60-89` (drag, then the token must be visible in cell 3,3 within 10 s).
- Frame handling: `services/board_state/ui/src/board-actions.ts:191-200` (`token_moved`, `connected`).
- The scenario fails more often when it runs alone, so the cause is likely an order or timing race between the board read, the board socket `connected` snapshot, the drag request, and the `token_moved` broadcast. Do not assume: find which of these the browser misses, then fix the cause.

## Documentation & Architecture Review

- `docs/explanation/realtime-voice-and-board-sync.md`, `docs/how-to/interact-with-tactile-board-and-ghost-previews.md`.
- TASK-0932 and the vtt-sync fix (the `connected` frame carries current tokens; the shell mounts the board after the board read).
- ADR-0015: a refused or lost move is shown, never hidden.

## Product & User Story References

- PRD-0005 (real-time board sync), US-0065.

## Detailed Specification & Implementation Plan

1. Reproduce the race in a frontdoor test (board-state HTTP and `/ws/boards` socket, or a vitest of the board element against a live loopback socket) before the fix.
2. Fix the cause so that every board that holds a socket shows each accepted move, whatever the order of the read, the snapshot, the move and the broadcast. A board state from an older read must never replace a newer frame.
3. Do not raise the e2e timeout and do not add sleeps or retries to the step.

## Frontdoor Blackbox Test Plan

- The new test fails before the fix and passes after it.
- Targeted board-state and board UI tests pass.
- Orchestrator on Kind: the scenario passes 12 of 12 with `--repeat-each=12`, then the full e2e suite passes.

## Definition of Done

- Tests pass. Docs updated if the frame order rules change. CHANGELOG `Fixed` entry.

## Audit Provenance

- Severity: high
- Source audits: .audit/work/vtt-repeat/run.log
