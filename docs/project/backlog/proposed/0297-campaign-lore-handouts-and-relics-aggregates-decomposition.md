---
id: '0297'
title: Campaign Lore Handouts and Relics Aggregates Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0101
governing_adrs:
- ADR-0002
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0015
governing_stories:
- US-0045
target_release: 0.8.0
---

# TASK-0297: Campaign Lore Handouts and Relics Aggregates Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/campaign_lore/src/campaign_lore/handouts_aggregate.py` (295 lines, 59.0% of limit) into modular aggregate modules under `services/campaign_lore/src/campaign_lore/aggregates/` (`handouts.py`, `relics.py`, `__init__.py`), keeping each aggregate module strictly < 160 lines per Hard Invariant 6.

## Problem Statement
`services/campaign_lore/src/campaign_lore/handouts_aggregate.py` defines two distinct `DeclarativeAggregate` classes and their associated Pydantic states in a single 295-line module:
1. `DiegeticHandoutState` and `DiegeticHandoutAggregate` (handles handout generation, wax seal cracking, invisible ink revelations)
2. `RelicState` and `RelicAggregate` (handles 3D relic forging, examination, and rune translation)

Coupling both aggregates into a single file limits modular maintainability as 3D WebGL mesh metadata and procedural alchemical recipe handouts are expanded.

## Governing Architecture & ADRs
- **ADR-0002: CloudEvents & eventsource-py Aggregates**: Enforces `DeclarativeAggregate` subclassing with `@handles` domain appliers.
- **ADR-0007: Domain-Driven Design Context Boundaries**: Isolates distinct entity lifecycles into dedicated aggregates.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 160 lines).

## Scope of Work
1. **Handouts Aggregate (`services/campaign_lore/src/campaign_lore/aggregates/handouts.py`)**:
   - Extract `DiegeticHandoutState` and `DiegeticHandoutAggregate` with its mutation methods and `@handles` appliers (< 150 lines).
2. **Relics Aggregate (`services/campaign_lore/src/campaign_lore/aggregates/relics.py`)**:
   - Extract `RelicState` and `RelicAggregate` with its mutation methods and `@handles` appliers (< 150 lines).
3. **Re-export Shim (`services/campaign_lore/src/campaign_lore/handouts_aggregate.py` or `aggregates/__init__.py`)**:
   - Maintain re-exports of `DiegeticHandoutAggregate`, `DiegeticHandoutState`, `RelicAggregate`, and `RelicState` for existing callers.
4. **Verification**:
   - Run `uv run pytest tests/test_blackbox_diegetic_handouts_and_relics.py` to ensure 100% test pass rate.

## Definition of Done
- `DiegeticHandoutAggregate` and `RelicAggregate` separated into dedicated files under `services/campaign_lore/src/campaign_lore/aggregates/`.
- All resulting modules strictly < 160 lines per Hard Invariant 6.
- 100% backwards compatibility preserved for all existing routers and tests.
- Passes all blackbox tests in `tests/test_blackbox_diegetic_handouts_and_relics.py`.
