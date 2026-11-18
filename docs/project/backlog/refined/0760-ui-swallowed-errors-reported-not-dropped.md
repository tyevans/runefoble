---
id: '0760'
title: UI Components Report Swallowed Errors Instead of Dropping Them
status: Refined
created: 2026-11-17
dependencies:
- TASK-0757
governing_adrs:
- ADR-0015
- ADR-0004
governing_prds:
- PRD-0005
governing_stories:
- US-0014
target_bc: board_state
target_release: 0.9.0
---
# TASK-0760: UI Components Report Swallowed Errors Instead of Dropping Them

## Status
Refined.

## Summary
TypeScript UI code drops errors with empty `catch {}`. A malformed WebSocket frame vanishes. Report these errors through one `runefoble-error` event. Keep only the pointer-capture guards, with a comment.

## Problem Statement
- `services/board_state/ui/src/runefoble-board.ts:127` (frame parse error dropped) and `:128` (socket setup error dropped).
- `services/voice_agent/ui/src/runefoble-mobile-companion.ts:123` and `:124`: same pattern.
- `frontend/src/components/minigames/runefoble-minigame-roulette.ts:180`, `runefoble-minigame-darts.ts:76`, `runefoble-minigame-liars-dice.ts:162`.
- `services/board_state/ui/src/radial_menu.ts:44` (check what it guards).
- Safe to keep with a comment: `releasePointerCapture` at `runefoble-board.ts:206`, `aoe_templates.ts:59` and `:77`; `navigator.vibrate` guards in `runefoble-mobile-companion.ts:46`, `:145`.
- The character sheet and rules lookup catches belong to TASK-0757.

## Documentation & Architecture Review
- ADR-0015 (no hidden failure). ADR-0004 (Storybook, zero console errors).
- The Python broad-except sweep (TASK-0699) does not cover TypeScript.

## Product & User Story References
- PRD-0005 (realtime board sync). US-0014.

## Detailed Specification & Implementation Plan
1. Add `reportError(host, source, error)` to `libs/runefoble_ui`. It dispatches a composed `runefoble-error` CustomEvent and logs to `console.error`.
2. Call it from each listed catch. The App Shell listens and shows one non-blocking notice.
3. Inspect `radial_menu.ts:44` and the three minigames. Remove the `try` where nothing can throw.
4. Add a one-line reason to every catch that stays empty.

## Frontdoor Blackbox Test Plan
- Playwright BDD: send a malformed frame through the live board WebSocket. Assert that the notice shows and the board still renders and accepts the next valid frame.
- Same check for the mobile companion socket.

## Definition of Done
- No empty `catch {}` without a reason comment in the listed files.
- Gates pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `frontend-ui`
