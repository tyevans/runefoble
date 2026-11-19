---
id: '0441'
title: Approved Audience Weather Modifier Changes the Game Session Weather
status: Refined
created: 2026-09-29
dependencies:
- TASK-0051
- TASK-0013
- TASK-0019
governing_adrs:
- ADR-0006
- ADR-0007
- ADR-0011
governing_prds:
- PRD-0001
- PRD-0011
governing_stories:
- US-0023
- US-0031
target_release: 0.9.0
---

# TASK-0441: Approved Audience Weather Modifier Changes the Game Session Weather

## Status
Refined

Audit 2026-11-17: event corrected to `AudienceModifierApproved` (`runefoble.events.audience.modifier_approved`, `libs/runefoble_events/src/runefoble_events/audience.py:75-89`) with the field `parameters`. The earlier name and field were not in the code. The subscriber work stays in this task.

Review 2026-11-18: rescoped. Each owner consumes `AudienceModifierApproved` for its own effect, so no owner writes the state of another one. This task covers `weather_change` in game_session. TASK-0835 covers `hazard_spawn` in board_state. TASK-0836 covers `status_buff` in character_sheet. TASK-0837 (item_drop) and TASK-0838 (Watcher narrative) are proposed, because their target model and AI contract are not decided.

## Summary
game_session consumes `AudienceModifierApproved` (`runefoble.events.audience.modifier_approved`, stream `runefoble.events.audience`). When the DM approves a `weather_change` modifier, the session of `session_id` records the new weather through its aggregate, and the public session read shows it.

## Problem Statement
An approved audience modifier is only a record in audience_studio. No service applies it, so the audience has no effect on the game (`docs/how-to/orchestrate-audience-chaos-polls.md`, line 80).

## Documentation & Architecture Review
- `docs/how-to/run-supervised-redis-stream-consumers.md`: the consumer pattern. Model: `services/board_state/src/board_state/forged_battlemap.py`.
- `docs/how-to/define-event-sourced-aggregates.md`: aggregate events and handlers.
- `docs/how-to/orchestrate-audience-chaos-polls.md`: the producer side.
- ADR-0006 (Redis Streams), ADR-0007 (DDD: each owner applies its own effect), ADR-0011 (eventsource-py), ADR-0015 (fail loud, no fallbacks).

## Product & User Story References
- [`prd-0011-live-spectator-studio-and-audience-interactivity.md`](../../product/accepted/prd-0011-live-spectator-studio-and-audience-interactivity.md)
- [`us-0031-live-stream-audience-chaos-polls-and-rumors.md`](../../user_stories/accepted/us-0031-live-stream-audience-chaos-polls-and-rumors.md)

## Detailed Specification & Implementation Plan
1. Add a session event for the weather change (for example `runefoble.events.session.weather_changed`, with `weather` and `source_proposal_id`). Register it, export it from `runefoble_events.events`, and regenerate the event catalogue.
2. The `GameSession` aggregate records the event. The public session read (`GET /api/v1/sessions/{id}`) returns the current `weather`.
3. Add a supervised consumer on `runefoble.events.audience` in the game_session lifespan. It acts only on `AudienceModifierApproved` with `approved is True` and `modifier_type == "weather_change"`. It ignores other modifier types: other owners apply them.
4. The weather value comes from `parameters["weather"]`. A missing or empty value raises, so the message goes to the dead-letter stream. A session that does not exist raises too.
5. Update `docs/how-to/orchestrate-audience-chaos-polls.md` and the events catalogue page.

## Frontdoor Test Plan
`tests/test_blackbox_audience_weather_modifier.py`, with the real lifespan and the shared Redis double:
- Create a session through public routes. Publish an approved `weather_change` modifier for it. The session read shows the new weather, and the weather event is on the session stream.
- A modifier with `approved: false` changes nothing.
- A `hazard_spawn` modifier changes nothing in game_session.
- A modifier without `parameters["weather"]` goes to the dead-letter stream, and the session is unchanged.

## INVEST Criteria Evaluation
- Independent: needs only the producer, which exists. Negotiable: the weather values are free text. Valuable: the first audience effect on the game. Estimable and Small: one event, one consumer, one test module. Testable: through a published standard event and the public session read.

## Definition of Done
1. The four test cases pass.
2. The event catalogue and the how-to are current.
3. `make health-check` passes.
