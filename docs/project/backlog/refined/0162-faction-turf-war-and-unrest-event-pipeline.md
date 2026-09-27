---
id: '0162'
title: Faction Turf War and Regional Unrest Event Pipeline
status: Refined
created: 2026-09-26
dependencies:
- TASK-0126
- TASK-0161
governing_adrs:
- ADR-0002
- ADR-0003
- ADR-0006
- ADR-0007
governing_prds:
- PRD-0017
- PRD-0007
governing_stories:
- US-0057
- US-0019
target_release: 0.7.0
---

# TASK-0162: Faction Turf War and Regional Unrest Event Pipeline

## Status
Refined

## Summary
Implement contested boundary skirmish calculations and regional unrest event fanout in `services/the_watcher/`, publishing `FactionTerritoryCaptured` and `RegionalUnrestEscalated` CloudEvents across Redis Streams without manual DM intervention.

## Problem Statement
When rival factions clash over territory, control nodes, or scarce resources, the system lacks an automated event-driven skirmish calculator. Territorial changes currently require manual DM intervention, and regional unrest does not dynamically ripple into guard alertness, tavern rumors, or encounter threat levels.

## Governing Architecture & ADRs
- **ADR-0002: Event-Driven Watcher Gameplay Orchestration**: Asynchronous world state mutation during background world ticks.
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout in `services/the_watcher/src/the_watcher/turf_war/`.
- **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Fanout of boundary clash and unrest events to `runefoble:events:world`.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation for faction clash mechanics and unrest metrics.

## Product & User Story References
- **Product Requirement**: [`prd-0017-autonomous-npc-faction-agendas-and-world-simulation.md`](../../product/accepted/prd-0017-autonomous-npc-faction-agendas-and-world-simulation.md)
- **User Story**: [`us-0057-autonomous-npc-faction-agendas-and-world-simulation.md`](../../user_stories/accepted/us-0057-autonomous-npc-faction-agendas-and-world-simulation.md)
- **User Story**: [`us-0019-ad-hoc-ephemeral-npc-spawning-and-scene-conditions.md`](../../user_stories/accepted/us-0019-ad-hoc-ephemeral-npc-spawning-and-scene-conditions.md)

## Detailed Specification & Implementation Plan
1. **Skirmish Adjudication Engine (`services/the_watcher/src/the_watcher/turf_war/skirmish_engine.py`)**:
   - Math evaluating faction military strength, terrain defensive advantages, and casualty calculations (< 140 lines).
2. **Regional Unrest Calculator (`services/the_watcher/src/the_watcher/turf_war/unrest_calculator.py`)**:
   - Metric tracker computing town unrest escalation, security levels, and economic friction (< 130 lines).
3. **CloudEvents Registration (`libs/runefoble_events/src/runefoble_events/turf_war.py`)**:
   - Define `FactionTerritoryCapturedEvent`, `RegionalUnrestEscalatedEvent`, and `FactionSkirmishResolvedEvent` (< 90 lines).
4. **World Event Dispatcher & REST API (`services/the_watcher/src/the_watcher/routers/turf_war.py`)**:
   - `POST /the-watcher/factions/skirmish/simulate`: Trigger ad-hoc skirmish resolution between two factions (< 130 lines).
   - `GET /the-watcher/regions/{region_id}/unrest`: Query unrest index and alert level (< 90 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Resolves faction skirmishes asynchronously during world simulation ticks without blocking active player combat turns.
- **Negotiable (N)**: Casualty modifiers and unrest escalation coefficients can be tuned via settings.
- **Valuable (V)**: Delivers a living, reactive sandbox where faction warfare shapes the world dynamically.
- **Estimable (E)**: Standard mathematical model and CloudEvents publication via Redis Streams.
- **Small (S)**: Bounded strictly to `services/the_watcher/src/the_watcher/turf_war/`; all modules < 150 lines.
- **Testable (T)**: Frontdoor blackbox tests verify simulated skirmishes, emitted events, and unrest query projections.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Domain Engine & Handlers**:
   - `services/the_watcher/src/the_watcher/turf_war/` created with focused submodules.
   - All modules strictly < 160 lines per Hard Invariant 6.
2. **Frontdoor Test Verification**:
   - Blackbox test suite `tests/test_blackbox_turf_war/` verifies skirmish execution, REST endpoints, and CloudEvent emission.
3. **Quality Gates**:
   - Passes `uv run pytest tests/test_blackbox_turf_war/`, `uv run ruff check .`, and `uv run ruff format --check .`.
