---
id: '0205'
title: West Marches Aggregate Discovery and Territory Handlers Modular Decomposition
status: Refined
created: 2026-09-27
dependencies:
- TASK-0127
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0011
governing_prds:
- PRD-0018
governing_stories:
- US-0050
- US-0058
target_release: 0.7.0
---

# TASK-0205: West Marches Aggregate Discovery and Territory Handlers Modular Decomposition

## Status
Refined

## Summary
Decompose `services/campaign_lore/src/campaign_lore/west_marches_aggregate.py` (304 lines, 60.8% of limit) by extracting discovery pin mutation logic, territory claim evaluations, and outpost fortification calculations into `west_marches_handlers.py`, keeping the root aggregate definition strictly < 150 lines per Hard Invariant 6 and ADR-0007.

## Problem Statement
`services/campaign_lore/src/campaign_lore/west_marches_aggregate.py` orchestrates multi-campaign shared persistent world state, communal points of interest, stronghold upgrades, and hex boundary claims. As Milestone 9 introduces cross-campaign settlements (TASK-0164) and frontier mercenary bounties (TASK-0165), new `@handles` methods and territory calculations will quickly drive this aggregate over 400 lines unless decoupled.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout in `services/campaign_lore/`.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation for shared world aggregates and event handlers.
- **ADR-0011: PostgreSQL Multi-Database Persistent Event Store**: Clean aggregate lifecycle management with `eventsource-py`.

## Detailed Specification & Implementation Plan
1. **Handlers Submodule (`services/campaign_lore/src/campaign_lore/west_marches_handlers.py`)**:
   - Extract domain calculation helpers, territory conflict validation, outpost fortification logic, and POI mutation routines (< 120 lines).
2. **Aggregate Refactoring (`services/campaign_lore/src/campaign_lore/west_marches_aggregate.py`)**:
   - Streamline `WestMarchesWorldAggregate` to retain declarative `@handles` routing that delegates state mutations to imported handler routines (< 150 lines).
3. **Verification**:
   - Run blackbox tests in `tests/test_blackbox_west_marches.py` and campaign lore unit tests to verify zero regressions.

## INVEST Criteria Evaluation
- **Independent (I)**: Internal modularization within `services/campaign_lore/`.
- **Negotiable (N)**: Pure refactoring preserving existing domain event types and aggregate public contracts.
- **Valuable (V)**: Protects event-sourced aggregate from bloating and maintains single responsibility.
- **Estimable (E)**: Follows the established aggregate decomposition pattern used across `game_session` and `board_state`.
- **Small (S)**: Scope restricted to separating mutation logic into handlers (< 150 lines per file).
- **Testable (T)**: Frontdoor verification via West Marches domain events and blackbox API routes.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Module Architecture**:
   - `west_marches_aggregate.py` reduced to < 150 lines.
   - `west_marches_handlers.py` created and strictly < 130 lines.
2. **Frontdoor Verification**:
   - All territory claims, outpost upgrades, and discovery pin events resolve cleanly.
   - All tests pass via `uv run pytest tests/test_blackbox_west_marches.py`.
3. **Quality Gates**:
   - Linting and formatting pass via `uv run ruff check .` and `uv run ruff format --check .`.
