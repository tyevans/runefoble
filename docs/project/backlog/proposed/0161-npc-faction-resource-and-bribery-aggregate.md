---
id: '0161'
title: NPC Faction Resource Operations and Bribery Mechanics Aggregate
status: Proposed
created: 2026-09-26
dependencies:
- TASK-0126
governing_adrs:
- ADR-0003
- ADR-0006
- ADR-0011
governing_prds:
- PRD-0017
governing_stories:
- US-0057
target_release: 0.7.0
---

# TASK-0161: NPC Faction Resource Operations and Bribery Mechanics Aggregate

## Status
Proposed

## Summary
Implement core domain aggregate handlers in `services/the_watcher/` for non-player faction resource expenditure, mercenary recruiting, and bribery difficulty calculations during inter-session world ticks.

## Problem Statement
While high-level faction agendas simulate territorial shifts, factions lack granular economic state tracking for bribery, smuggling bribes, and covert operations that react dynamically to player diplomacy and merchant wealth.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout in `services/the_watcher/`.
- **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Event emission for resource mutations.
- **ADR-0011: PostgreSQL Event Store via Eventsource-py**: DeclarativeAggregate pattern.

## Scope of Work
1. **Faction Resource State Models**:
   - Pydantic models and aggregate state handlers for treasury gold, mercenary units, and black-market contraband.
2. **Bribery and Influence Operations**:
   - Adjudication logic computing bribe success thresholds against city watch alertness and rival counter-bribes.
3. **Frontdoor Verification**:
   - Unit tests validating state transitions, event publication, and treasury balance invariant checks.

## Definition of Done
- Aggregate models implemented in `services/the_watcher/src/the_watcher/`.
- Domain events registered with `@register_event`.
- Unit tests pass with `uv run pytest`.
- File length remains under 300 lines.
