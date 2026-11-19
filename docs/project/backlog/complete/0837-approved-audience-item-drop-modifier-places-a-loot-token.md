---
id: '0837'
title: Approved Audience Item Drop Modifier Places a Loot Token on the Board
status: Complete
created: 2026-11-18
dependencies:
- TASK-0835
- TASK-0843
governing_adrs:
- ADR-0006
- ADR-0007
- ADR-0011
governing_prds:
- PRD-0011
governing_stories:
- US-0031
target_release: 0.9.0
---

# TASK-0837: Approved Audience Item Drop Modifier Places a Loot Token on the Board

## Status
Complete

Decision (user, 2026-11-18): the dropped item becomes a loot token on the board. Pick-up into a character inventory is a later task.

## Summary
board_state consumes `AudienceModifierApproved` on `runefoble.events.audience` (the same supervised consumer set as the TASK-0835 hazard consumer). An approved `item_drop` modifier places a loot token on the board of `session_id` at the cell it names. The public board read shows the token with its item name.

## Documentation & Architecture Review
- `docs/how-to/orchestrate-audience-chaos-polls.md` (consumer contract), `docs/how-to/interact-with-tactile-board-and-ghost-previews.md` (token types), `docs/reference/events-catalog-world-media.md`.
- Model: `services/board_state/src/board_state/audience_hazard.py` and the shared helper `runefoble_platform.audience_modifiers` (TASK-0843).
- ADR-0006, ADR-0007 (each owner applies its own effect), ADR-0011, ADR-0015 (fail loud).

## Product & User Story References
- [`prd-0011-live-spectator-studio-and-audience-interactivity.md`](../../product/accepted/prd-0011-live-spectator-studio-and-audience-interactivity.md)
- [`us-0031-live-stream-audience-chaos-polls-and-rumors.md`](../../user_stories/accepted/us-0031-live-stream-audience-chaos-polls-and-rumors.md)

## Detailed Specification & Implementation Plan
1. Add an `item_drop` consumer to the board_state audience consumers. Use the shared helper for the approved check, the type filter, the parameters and the campaign-match guard.
2. Parameters: `x`, `y` (integers on the grid) and `item_name` (non-blank text). Optional `item_id` (text). A missing or bad parameter, a cell off the grid, a cell that a token already holds, or a board of another campaign raises, so the message goes to the dead-letter stream.
3. Place the token through the board aggregate with a loot token type (for example `token_type: "loot"`), the item name as the token name, and the source proposal id. Use the existing token placement event; add a field only if the event cannot carry the item.
4. The public board read and the spectator view show the loot token. A loot token is not a combatant and does not block movement.
5. Update the docs above and the events catalogue page.

## Frontdoor Test Plan
With the real board_state lifespan and the shared Redis double:
- Create a board through public routes. Publish an approved `item_drop` at a free cell. The board read shows a `loot` token with the item name at that cell.
- A vetoed modifier, another modifier type, a cell off the grid, an occupied cell, a missing `item_name`, and a modifier of another campaign change nothing; the invalid ones go to the dead-letter stream.
- A token can move onto the loot cell (it does not block).

## INVEST Criteria Evaluation
Small: one consumer branch and one test module. Testable through a published standard event and the public board read.

## Definition of Done
1. The test cases pass. 2. Docs and catalogue are current. 3. `make health-check` passes.
