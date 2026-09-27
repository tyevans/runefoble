---
id: '0161'
title: NPC Faction Resource Operations and Bribery Mechanics Aggregate
status: Complete
created: 2026-09-26
dependencies:
- TASK-0126
governing_adrs:
- ADR-0003
- ADR-0006
- ADR-0007
- ADR-0011
governing_prds:
- PRD-0017
governing_stories:
- US-0057
target_release: 0.7.0
pr_url: https://github.com/tyevans/runefoble/pull/184
---
# TASK-0161: NPC Faction Resource Operations and Bribery Mechanics Aggregate

## Status
Refined

## Summary
Implement core domain aggregate handlers in `services/the_watcher/` for non-player faction resource expenditure, mercenary recruiting, and bribery difficulty calculations during inter-session world ticks.

## Problem Statement
While high-level faction agendas simulate territorial shifts, factions lack granular economic state tracking for bribery, smuggling bribes, and covert operations that react dynamically to player diplomacy and merchant wealth.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout in `services/the_watcher/`.
- **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Event emission for resource mutations.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain aggregate models and business logic.
- **ADR-0011: PostgreSQL Event Store via Eventsource-py**: DeclarativeAggregate pattern.

## Product & User Story References
- **Product Requirement**: [`prd-0017-autonomous-npc-factions-and-living-world.md`](../../product/accepted/prd-0017-autonomous-npc-factions-and-living-world.md)
- **User Story**: [`us-0057-autonomous-npc-faction-agendas.md`](../../user_stories/accepted/us-0057-autonomous-npc-faction-agendas.md)

## Detailed Specification & Implementation Plan
1. **Faction Resource Models (`services/the_watcher/src/the_watcher/factions/resources/models.py`)**:
   - Pydantic models for treasury gold, mercenary units, and contraband (< 120 lines).
2. **Resource Aggregate Handlers (`services/the_watcher/src/the_watcher/factions/resources/aggregate.py`)**:
   - Event-sourced state transitions for spending, income collection, and unit upkeep (< 140 lines).
3. **Bribery & Influence Resolver (`services/the_watcher/src/the_watcher/factions/resources/bribery.py`)**:
   - Adjudication logic computing DC thresholds against target loyalty and counter-bribes (< 130 lines).
4. **CloudEvents Registration (`libs/runefoble_events/src/runefoble_events/faction_resources.py`)**:
   - Define `FactionResourceUpdatedEvent`, `FactionBriberyAttemptedEvent`, and `FactionMercenaryRecruitedEvent` (< 90 lines).
5. **Frontdoor API Endpoints (`services/the_watcher/src/the_watcher/routers/faction_resources.py`)**:
   - `POST /factions/{faction_id}/resources/adjust`: Adjust faction assets.
   - `POST /factions/{faction_id}/bribery/resolve`: Execute bribery attempt and emit event.

## INVEST Criteria Evaluation
- **Independent (I)**: Expands the faction simulation engine without blocking current tactical board play.
- **Negotiable (N)**: Economic curves and bribery difficulty formulas can be re-tuned.
- **Valuable (V)**: Allows living world factions to deploy economic warfare and bribery against player parties.
- **Estimable (E)**: Standard eventsource aggregate and mathematical resolution.
- **Small (S)**: Bounded strictly to `services/the_watcher/src/the_watcher/factions/resources/`; all files < 160 lines.
- **Testable (T)**: Frontdoor blackbox tests verify REST endpoints and CloudEvents.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Domain Engine & Handlers**:
   - `services/the_watcher/src/the_watcher/factions/resources/` created with focused submodules.
   - All modules strictly < 160 lines per Hard Invariant 6.
2. **Frontdoor Test Verification**:
   - Blackbox test suite `tests/test_blackbox_faction_resources/` verifies resource updates and bribery outcomes via public HTTP routes.
3. **Quality Gates**:
   - Passes `uv run pytest tests/test_blackbox_faction_resources/`, `uv run ruff check .`, and `uv run ruff format --check .`.
