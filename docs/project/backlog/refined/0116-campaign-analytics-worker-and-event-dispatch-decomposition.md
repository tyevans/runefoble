---
id: '0116'
title: Campaign Analytics Worker and Event Dispatch Modular Decomposition
status: Refined
created: 2026-09-26
dependencies:
- TASK-0052
- TASK-0082
governing_adrs:
- ADR-0003
- ADR-0006
- ADR-0011
target_release: 0.4.0
governing_prds:
- PRD-0012
governing_stories:
- US-0040
- US-0054
---

# TASK-0116: Campaign Analytics Worker and Event Dispatch Modular Decomposition

## Status
Refined

## Summary
Decompose `services/campaign_analytics/src/campaign_analytics/worker.py` (420 lines, 84.0% of limit) into an asynchronous worker orchestration module (`worker.py`) and a specialized event projection dispatcher (`event_handlers.py`) to prevent violating Hard Invariant 6 (File length limit < 500 lines).

## Problem Statement
`services/campaign_analytics/src/campaign_analytics/worker.py` currently couples two distinct responsibilities into 420 lines:
1. Worker lifecycle: Redis Streams connection management, consumer group registration, continuous polling loops, task lifecycle cancellation, and graceful shutdown.
2. Domain event dispatch and projection logic: Inspecting CloudEvents and event types (`SessionCreated`, `SessionStarted`, `SessionEnded`, `CombatEncounterStarted`, `CombatRoundAdvanced`, `TokenPlaced`, `TokenMoved`, `DiceRolled`, `CharacterHealthChanged`, `AbsenteeRecapGenerated`), tracking ephemeral token positions, calculating spatial distances, and invoking storage persistence methods.

Adding new event types will quickly push `worker.py` past the 500-line hard invariant limit.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module decomposition inside `services/campaign_analytics/`.
- **ADR-0006: Redis Streams Distributed Event Bus**: Preserving consumer group semantics, message delivery guarantees, and event stream parsing.
- **ADR-0011: eventsource-py Core Event Sourcing**: Handling standard domain events from `libs/runefoble_events`.

## Product & User Story References
- **Product Requirement**: [`prd-0012-campaign-telemetry-and-living-chronicle-timeline.md`](../../product/accepted/prd-0012-campaign-telemetry-and-living-chronicle-timeline.md)
- **User Stories**:
  - [`us-0040-campaign-combat-telemetry-and-living-timeline.md`](../../user_stories/accepted/us-0040-campaign-combat-telemetry-and-living-timeline.md)
  - [`us-0054-combat-spatial-heatmaps-and-party-damage-analytics.md`](../../user_stories/accepted/us-0054-combat-spatial-heatmaps-and-party-damage-analytics.md)

## Detailed Specification & Implementation Plan
1. **Event Projection Handlers (`services/campaign_analytics/src/campaign_analytics/event_handlers.py`)**:
   - Extract handler functions for spatial movements (`TokenPlaced`, `TokenMoved`), combat rounds (`CombatRoundAdvanced`), damage/healing (`CharacterHealthChanged`), dice rolls (`DiceRolled`), and chronicles (`AbsenteeRecapGenerated`) (< 200 lines).
   - Ephemeral token tracking state and helper calculations isolated from Redis loop logic.
2. **Worker Coordination Core (`services/campaign_analytics/src/campaign_analytics/worker.py`)**:
   - `CampaignAnalyticsWorker` coordinating Redis consumer group polling, batch processing, acknowledgment, and error handling (< 180 lines).
   - Delegates event translation to `handle_domain_event()` or registered handler functions.

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors internal worker structure without changing the external Redis Streams consumer contract or storage data schema.
- **Negotiable (N)**: Function-based dispatch table vs class-based handler hierarchy.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (< 500 lines) and enables clean addition of new event projections.
- **Estimable (E)**: Standard Python event dispatch refactoring.
- **Small (S)**: Scope strictly isolated to `services/campaign_analytics/src/campaign_analytics/worker.py`; both resulting modules < 220 lines.
- **Testable (T)**: Verified with `tests/test_blackbox_campaign_analytics.py` and unit tests.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Module Separation**:
   - `worker.py` and `event_handlers.py` created with clean interfaces.
2. **File Size Limit**:
   - All modules in `services/campaign_analytics/` strictly under 250 lines in compliance with Hard Invariant 6.
3. **Public Contract Preserved**:
   - `CampaignAnalyticsWorker` maintains 100% backward-compatible initialization and public methods (`start()`, `stop()`, `process_event()`).
4. **Frontdoor Blackbox Verification**:
   - All blackbox tests pass cleanly with `uv run pytest tests/test_blackbox_campaign_analytics*.py`.
