---
id: '0974'
title: The Session View Reads the Caller's Seat, Including the Stand-In State
status: Complete
created: 2026-11-20
dependencies:
- '0952'
- '0954'
- '0972'
governing_adrs:
- ADR-0013
- ADR-0014
- ADR-0015
governing_prds:
- PRD-0002
- PRD-0025
governing_stories:
- us-0065-game-session-lobby-readiness-and-launch
target_bc: frontend
target_release: 1.0.0
---

# TASK-0974: The Session View Reads the Caller's Seat, Including the Stand-In State

## Status

Complete

## Summary

On Kind (2026-11-20), Sarah marked herself absent in the lobby, opened the active session, and saw no "Stance Directives" button. Since TASK-0952, game_session holds the stand-in state on the session participant (`services/game_session/src/game_session/models/session.py:19`, `is_stand_in_active`). The session view still reads the stand-in flag from the character record (`frontend/src/app/absentee-actions.ts:32`, character_sheet `is_stand_in_active`), which the lobby no longer changes. Also, the session load reads seats only for a DM without a board (`frontend/src/app/session-data-loader.ts`, `needsSeats`), so the caller's own seat is unknown, and the own-character binding (TASK-0972) cannot prefer it.

## Detailed Specification & Implementation Plan

1. The session load always reads the session state (`GET /api/v1/sessions/{id}`) and maps each participant with `player_id`, `character_id`, `character_name` and `is_stand_in_active`. Keep the board set-up seat list (`PartySeat`) as it is for the DM; add the caller's own seat to the host.
2. `resolveActiveCharacter` prefers the character of the caller's own seat (TASK-0972 rule: only the caller's own character).
3. The bound character's stand-in state in the session view comes from the caller's seat. The stance drawer button shows only when the caller's seat is an active stand-in. Remove the read of the character record flag for this purpose. A live `player_stand_in` frame updates the seat state.
4. Fix the e2e setup of `e2e/features/session_view_controls.feature`, scenario "The DM board shows no hidden-layer toggle": add `And Valeros opens the lobby of "Stance Lobby"` before `Evelyn launches the session and sets up the battlemap`, because that step waits for Valeros to follow the launch.
5. Lit rule: bind object and array inputs through `guard` (docs/how-to/develop-lit-components-in-storybook.md section 11).

## Frontdoor Blackbox Test Plan

- Node tests of the loader with a fetch fake: the caller's seat and its stand-in state are read on every session load; a player with no seat has none; a `player_stand_in` frame updates it.
- Orchestrator on Kind: `session_view_controls.feature` passes (all three scenarios), and the full suite passes.
