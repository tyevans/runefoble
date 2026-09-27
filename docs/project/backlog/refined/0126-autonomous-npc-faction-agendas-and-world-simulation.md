---
id: '0126'
title: Autonomous NPC Faction Agendas & Background Simulation Engine
status: Refined
created: 2026-09-26
dependencies:
- TASK-0013
- TASK-0047
governing_adrs:
- ADR-0002
- ADR-0006
- ADR-0011
governing_prds:
- PRD-0001
governing_stories:
- US-0057
target_release: 0.5.0
---

# TASK-0126: Autonomous NPC Faction Agendas & Background Simulation Engine

## Status
Refined

## Summary
Build a background world progression engine for The Watcher where non-player factions, secret cults, and rival guilds execute goal-oriented agenda ticks between game sessions, generating dynamic geopolitical shifts, trade shortages, and evolving tavern rumors.

## Problem Statement
Between gaming sessions, the campaign world currently remains frozen in time unless the DM manually writes lore updates (PRD-0001, US-0057). DMs like Evelyn need an autonomous simulation engine that ticks faction resources, simulates rival clashes, and outputs concise intelligence briefs.

## Governing Architecture & ADRs
- **ADR-0002: Event-Driven Watcher Gameplay Orchestration**: Simulation loop executed via background Celery/Redis Stream worker.
- **ADR-0006: Redis Streams Event Bus**: Event dispatch for `WorldTickExecuted`, `FactionAgendaAdvanced`, and `GeopoliticalShiftOccurred`.
- **ADR-0011: eventsource-py Core Event Sourcing**: `FactionAggregate` tracking faction assets, goals, and geopolitical relationships.

## Product & User Story References
- **Product Requirement**: [`prd-0001-the-watcher-ai-dm-and-board-animator.md`](../../product/accepted/prd-0001-the-watcher-ai-dm-and-board-animator.md)
- **User Story**: [`us-0057-autonomous-npc-faction-agendas-and-world-simulation.md`](../../user_stories/accepted/us-0057-autonomous-npc-faction-agendas-and-world-simulation.md)

## Detailed Specification & Implementation Plan
1. **Faction Domain Modeling (`services/the_watcher/src/the_watcher/factions.py`)**:
   - `FactionAggregate` with attributes: name, influence (1-100), resources, disposition towards party, and active goal (e.g. "Infiltrate Arcane Guild").
2. **Simulation Tick Engine**:
   - Probabilistic resolution of agenda checks based on rival faction counter-measures and regional stability modifiers.
3. **DM Intelligence Bulletin Generator**:
   - Generates bulleted narrative briefing summarizing geopolitical developments, territorial control changes, and new tavern rumors.
4. **Frontdoor Blackbox Verification**:
   - Blackbox test suite exercising `/api/v1/campaigns/{id}/factions/tick` and asserting event persistence and rumor generation.

## INVEST Criteria Evaluation
- **Independent (I)**: Runs independently between active live sessions.
- **Negotiable (N)**: Tick frequency (manual DM trigger vs scheduled cron) is configurable.
- **Valuable (V)**: Delivers a living, breathing world that responds dynamically to player choices.
- **Estimable (E)**: Follows existing aggregate and event sourcing patterns in `the_watcher`.
- **Small (S)**: Scope strictly isolated to `services/the_watcher/`; all files < 320 lines.
- **Testable (T)**: Fully verifiable via public REST simulation endpoints and domain event assertions.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Faction Aggregate & Event Appliers**:
   - `FactionAggregate` in `services/the_watcher/` handling goal initialization, resource progression, and conflict resolution.
2. **Downtime Simulation Endpoint**:
   - Public HTTP route `POST /api/v1/campaigns/{id}/world-tick` advancing faction agendas and returning generated intelligence bulletins.
3. **Frontdoor Blackbox Test Suite**:
   - `tests/test_blackbox_faction_simulation.py` verifying faction progression, conflict roll resolution, and event emissions.
4. **Quality Gates**:
   - Conforms to Hard Invariant 6 (< 500 lines per file).
   - Passes `uv run pytest tests/test_blackbox_faction_simulation.py`.
