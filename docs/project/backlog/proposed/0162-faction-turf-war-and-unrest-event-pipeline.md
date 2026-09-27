---
id: '0162'
title: Faction Turf War and Regional Unrest Event Pipeline
status: Proposed
created: 2026-09-26
dependencies:
- TASK-0126
- TASK-0161
governing_adrs:
- ADR-0002
- ADR-0006
governing_prds:
- PRD-0017
governing_stories:
- US-0057
- US-0019
target_release: 0.7.0
---

# TASK-0162: Faction Turf War and Regional Unrest Event Pipeline

## Status
Proposed

## Summary
Implement contested boundary skirmish calculations and regional unrest event fanout in `services/the_watcher/`, publishing `FactionTerritoryCaptured` and `RegionalUnrestEscalated` CloudEvents across Redis Streams.

## Problem Statement
When rival factions clash over territory or resources, the system must calculate collision casualties, district control shifts, and unrest ripple effects without manual DM intervention.

## Governing Architecture & ADRs
- **ADR-0002: Event-Driven Watcher Gameplay Orchestration**: World state mutation lifecycle.
- **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Fanout of boundary clash events.

## Scope of Work
1. **Contested Border Skirmish Adjudication**:
   - Math evaluating faction military strength, local terrain advantage, and roll modifiers.
2. **Regional Unrest Event Dispatch**:
   - CloudEvent publishing for territory transitions, guard alertness escalation, and tavern rumors.
3. **Frontdoor Verification**:
   - Integration tests asserting event publication and downstream handler consumption.

## Definition of Done
- Skirmish resolver implemented in `the_watcher`.
- Domain events emitted to Redis Streams `runefoble:events:world`.
- Tests pass cleanly via `uv run pytest`.
- Module length stays below 250 lines.
