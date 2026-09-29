---
id: '0441'
title: Audience Chaos Modifiers Event Bridge & Game Session Mutation Handlers
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

# TASK-0441: Audience Chaos Modifiers Event Bridge & Game Session Mutation Handlers

## Status
Refined

## Summary
Implement Redis Streams domain event subscribers in `services/game_session` and `services/the_watcher` for `AudienceProposalApproved` domain events. Translate approved audience chaos modifiers (e.g. weather shifts, environmental hazards, wild magic surges, tavern brawls, consumable item drops) into concrete `GameSession` aggregate mutations, board state updates, and Watcher narrative commentary events.

## Problem Statement
When a DM approves an audience chaos poll outcome in `services/audience_studio`, an `AudienceProposalApproved` CloudEvent is published to the Redis event stream. However, neither `game_session` nor `the_watcher` currently listens to this event topic. Consequently, approved audience modifiers remain purely cosmetic records in the audience studio database and never affect the active tactical board, party inventory, or narrative gameplay.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/orchestrate-audience-chaos-polls.md`: Event routing between Audience Studio, Game Session, and The Watcher.
  - `docs/how-to/define-event-sourced-aggregates.md`: DeclarativeAggregate mutation handlers and event publication.
  - `docs/reference/events-schema.md`: CloudEvents payloads for audience proposals and mechanical modifiers.
- **Governing Architecture & ADRs**:
  - **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Consumer group message processing across bounded contexts.
  - **ADR-0007: Domain-Driven Design Architecture**: Cross-context event handling between Audience Studio, Game Session, and The Watcher.
  - **ADR-0011: Event Sourcing with Eventsource-py**: State transitions recorded via immutable domain events.

## Product & User Story References
- [`prd-0001-the-watcher-ai-dm-and-board-animator.md`](../../product/accepted/prd-0001-the-watcher-ai-dm-and-board-animator.md)
- [`prd-0011-live-spectator-studio-and-audience-interactivity.md`](../../product/accepted/prd-0011-live-spectator-studio-and-audience-interactivity.md)
- [`us-0023-spoken-reaction-interrupts-and-ready-actions.md`](../../user_stories/accepted/us-0023-spoken-reaction-interrupts-and-ready-actions.md)
- [`us-0031-live-stream-audience-chaos-polls-and-rumors.md`](../../user_stories/accepted/us-0031-live-stream-audience-chaos-polls-and-rumors.md)

## Detailed Specification & Implementation Plan
1. **CloudEvents Definition (`libs/runefoble_events/src/runefoble_events/audience.py`)**:
   - Verify `AudienceProposalApproved` CloudEvent schema with fields: `campaign_id`, `session_id`, `proposal_id`, `modifier_type`, `description`, `mechanical_payload`.
2. **GameSession Event Handler (`services/game_session/src/game_session/event_handlers.py`)**:
   - Subscribe to `AudienceProposalApproved`.
   - Apply mechanical payloads:
     - `weather_change`: Update environmental conditions (e.g. dense fog, thunderstorm, rain).
     - `hazard_spawn`: Dispatch hazard placement event to `board_state`.
     - `item_drop`: Add consumable item (e.g. potion, mysterious scroll) to ground loot or party stash.
     - `status_buff`: Apply minor temporary condition (blessed, inspired).
3. **The Watcher Narrative Handler (`services/the_watcher/src/the_watcher/handlers/audience.py`)**:
   - Ingest approved audience modifier and trigger The Watcher AI to compose immersive narrative commentary describing the audience-driven twist.
4. **Blackbox Tests (`tests/test_blackbox_audience_chaos_event_bridge.py`)**:
   - Publish `AudienceProposalApproved` event to the platform event bus and assert that `GameSession` state reflects the modifier and `WatcherNarrativeDispatched` event is emitted.

## INVEST Criteria Evaluation
- **Independent (I)**: Decoupled via CloudEvents; both producer and consumers interact via standard event topics.
- **Negotiable (N)**: Specific list of modifier mechanical effects can expand over time.
- **Valuable (V)**: Bridges viewer engagement with actual in-game tactical consequences.
- **Estimable (E)**: Standard eventsource-py aggregate pattern.
- **Small (S)**: Handler implementations < 100 lines and one blackbox test file.
- **Testable (T)**: Frontdoor event dispatching asserting published CloudEvents and aggregate projections.

## Definition of Done
1. `AudienceProposalApproved` subscribed in `game_session` and `the_watcher`.
2. Approved modifiers apply concrete mechanical effects to the session and trigger Watcher narrative commentary.
3. Frontdoor blackbox test suite `tests/test_blackbox_audience_chaos_event_bridge.py` passes with 100% assertions.
4. Code passes `uv run ruff check .` and `uv run ruff format --check .`.
