---
id: '0690'
title: Leaving a Session Activates the Character Stand-In in Character Sheet
status: Refined
created: 2026-11-17
dependencies:
- TASK-0548
- TASK-0586
governing_adrs:
- ADR-0015
governing_prds:
- PRD-0002
governing_stories:
- US-0002
- US-0026
target_release: 0.9.0
severity: high
source_audits:
- work/0570.md
---

# TASK-0690: Leaving a Session Activates the Character Stand-In in Character Sheet

## Status
Refined. Discovered in round 2 audit of report 0570. PRD-0002 requires the stand-in to take over an absent player's character. No production path does this.

## Summary
`game_session` records a player's absence in its own projection. It never calls the character sheet to set `is_stand_in_active`. The stand-in flag is therefore never set in production. This task wires the leave route to the character sheet stand-in route, with the penalties and guardrails that already exist.

## Problem Statement
- `services/game_session/src/game_session/routers/session.py:90-99`: `leave_session` calls `session.leave_player` and saves. It makes no call to character sheet.
- No HTTP caller of `POST /api/v1/characters/{character_id}/stand-in` exists in `services/game_session/src`. The route exists at `services/character_sheet/src/character_sheet/router.py:88`.
- `RUNEFOBLE_CHARACTER_SHEET_URL` is already set for game-session in Helm (`services.yaml:22`).
- The gateway store flag is a second source of truth (TASK-0586).

## Documentation & Architecture Review
- ADR-0015 (a): the owner of the character (character_sheet) writes the stand-in state. game_session sends the command.
- ADR-0015 (b): if character sheet fails, the leave route returns 503. It does not record a fake activation.
- `docs/how-to/configure-stand-in-guardrails-and-hot-swap.md`: state the leave path.

## Product & User Story References
- PRD-0002 and US-0002 (autonomous stand-in). US-0026 (hot-swap takeover). The stand-in keeps the game going when a player leaves.

## Detailed Specification & Implementation Plan
1. In `leave_session`, find the character the player brought to the lobby (`select_lobby_character`). If there is none, record the absence only, as today, and state that in the response.
2. Call character sheet `POST /api/v1/characters/{character_id}/stand-in` with `active: true` and the session id, through the shared service client.
3. If the call fails, return 503 and do not save the leave. Save only after the character sheet accepts.
4. On rejoin or hot-swap, clear the flag through the same route. Confirm TASK-0548 covers this path.

## Frontdoor Blackbox Test Plan
- Create a campaign and a session through public routes. A player joins and selects a character.
- The player calls the public leave route. Then read the character through the public character route. Assert `is_stand_in_active` is true and the absence penalty applies.
- Stop character sheet (test double returns 503). The leave route returns 503 and the session state does not change.
- Rejoin. The flag is cleared.

## Definition of Done
- Leave activates the stand-in in character sheet. The flag is set in production code, not only in tests.
- `uv run pytest` and `make lint` pass. Docs updated.
