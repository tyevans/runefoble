---
id: '0835'
title: Approved Audience Hazard Modifier Places a Hazard on the Board
status: Refined
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

# TASK-0835: Approved Audience Hazard Modifier Places a Hazard on the Board

## Status
Refined

## Summary
board_state consumes `AudienceModifierApproved` on `runefoble.events.audience`. An approved `hazard_spawn` modifier places a hazard cell on the board of `session_id`.

## Product & User Story References
- [`prd-0011-live-spectator-studio-and-audience-interactivity.md`](../../product/accepted/prd-0011-live-spectator-studio-and-audience-interactivity.md)
- [`us-0031-live-stream-audience-chaos-polls-and-rumors.md`](../../user_stories/accepted/us-0031-live-stream-audience-chaos-polls-and-rumors.md)

## Documentation & Architecture Review
- `docs/how-to/run-supervised-redis-stream-consumers.md` and the model consumer `services/board_state/src/board_state/forged_battlemap.py`.
- `docs/how-to/orchestrate-audience-chaos-polls.md`.
- ADR-0006, ADR-0007 (each owner applies its own effect), ADR-0011, ADR-0015 (fail loud).

## Detailed Specification & Implementation Plan
1. Add a second `StreamConsumer` on `runefoble.events.audience` to the board_state supervised consumers.
2. Act only on `approved is True` and `modifier_type == "hazard_spawn"`. Read `x`, `y` and `hazard_type` from `parameters`. Apply them through the board aggregate (`configure_terrain`), which owns the bounds check and the hazard table.
3. A missing parameter, an unknown hazard type, a cell off the grid, or a board that does not exist raises, so the message goes to the dead-letter stream.
4. Update the events catalogue page and the chaos-poll how-to.

## Frontdoor Test Plan
With the real board_state lifespan and the shared Redis double: create a board through public routes; publish an approved `hazard_spawn`; the public board read shows the hazard. A vetoed modifier and a `weather_change` modifier change nothing. A cell off the grid goes to the dead-letter stream.

## INVEST Criteria Evaluation
Small: one consumer and one test module. Testable through a published standard event and the public board read.

## Definition of Done
1. The test cases pass. 2. Docs are current. 3. `make health-check` passes.
