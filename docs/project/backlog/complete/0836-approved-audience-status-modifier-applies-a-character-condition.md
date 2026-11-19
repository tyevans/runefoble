---
id: '0836'
title: Approved Audience Status Modifier Applies a Condition to a Character
status: Complete
created: 2026-11-18
dependencies:
- TASK-0441
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

# TASK-0836: Approved Audience Status Modifier Applies a Condition to a Character

## Status
Complete

## Summary
character_sheet consumes `AudienceModifierApproved` on `runefoble.events.audience`. An approved `status_buff` modifier applies a condition (for example `blessed` or `inspired`) to the character named in `parameters["character_id"]`.

## Product & User Story References
- [`prd-0011-live-spectator-studio-and-audience-interactivity.md`](../../product/accepted/prd-0011-live-spectator-studio-and-audience-interactivity.md)
- [`us-0031-live-stream-audience-chaos-polls-and-rumors.md`](../../user_stories/accepted/us-0031-live-stream-audience-chaos-polls-and-rumors.md)

## Documentation & Architecture Review
- `docs/how-to/run-supervised-redis-stream-consumers.md` and the model consumer `services/board_state/src/board_state/forged_battlemap.py`.
- `docs/how-to/orchestrate-audience-chaos-polls.md`.
- ADR-0006, ADR-0007 (each owner applies its own effect), ADR-0011, ADR-0015 (fail loud).

## Detailed Specification & Implementation Plan
1. Add a supervised consumer on `runefoble.events.audience` in the character_sheet lifespan.
2. Act only on `approved is True` and `modifier_type == "status_buff"`. Apply the condition through the character aggregate and its existing condition model (`services/character_sheet/src/character_sheet/models/conditions.py`).
3. A missing `character_id` or `condition`, an unknown condition, or a character that does not exist raises, so the message goes to the dead-letter stream.
4. The character must be in the campaign of the modifier. A character of another campaign raises.
5. Update the events catalogue page and the chaos-poll how-to.

## Frontdoor Test Plan
With the real character_sheet lifespan and the shared Redis double: create a character through public routes; publish an approved `status_buff`; the public character read shows the condition. A vetoed modifier, another modifier type, and a character of another campaign change nothing.

## INVEST Criteria Evaluation
Small: one consumer and one test module. Testable through a published standard event and the public character read.

## Definition of Done
1. The test cases pass. 2. Docs are current. 3. `make health-check` passes.
