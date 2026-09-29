---
id: '0343'
title: West Marches Domain Models Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0127
- TASK-0205
governing_adrs:
- ADR-0003
- ADR-0006
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0018
governing_stories:
- US-0058
target_release: 0.8.0
---

# TASK-0343: West Marches Domain Models Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/game_session/src/game_session/west_marches.py` (281 lines, 56.2% of limit) into modular submodules under `services/game_session/src/game_session/west_marches/` (`models.py`, `aggregate.py`, `handlers.py`), with an aggregator export at `services/game_session/src/game_session/west_marches.py`, ensuring all submodules remain strictly < 110 lines per Hard Invariant 6.

## Problem Statement
`services/game_session/src/game_session/west_marches.py` bundles the `SharedWorldState` Pydantic models, aggregate initialization, creation handlers, outpost establishment logic, communal tavern notice posting, and discovery registration in a single file. As regional settlement federations, territory dispute resolutions, and caravan outpost trading are expanded, this file will approach the 500-line limit unless modularized into focused domain components.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout and packaging.
- **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Real-time event propagation and stream broadcasting.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain boundaries and event-sourced aggregates.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 110 lines).

## Scope of Work
1. **Shared State Models (`services/game_session/src/game_session/west_marches/models.py`)**:
   - Extract `SharedWorldState` Pydantic model and UUID helper functions (< 50 lines).
2. **Event Handlers (`services/game_session/src/game_session/west_marches/handlers.py`)**:
   - Extract outpost, stronghold upgrade, communal notice, and discovery handlers (< 100 lines).
3. **Aggregate Implementation (`services/game_session/src/game_session/west_marches/aggregate.py`)**:
   - Extract `SharedWorldAggregate` class and lifecycle methods (< 95 lines).
4. **Aggregator Entry Point (`services/game_session/src/game_session/west_marches.py`)**:
   - Re-export all public models and aggregates for seamless backwards compatibility (< 25 lines).
5. **Verification**:
   - Ensure existing tests pass via `uv run pytest tests/test_caravan_modular_decomposition.py` and all West Marches tests.

## Definition of Done
- `services/game_session/src/game_session/west_marches/` submodules strictly < 110 lines each per Hard Invariant 6.
- Root `west_marches.py` reduced to a backwards-compatible re-export module (< 30 lines).
- Passes all tests via `uv run pytest`.
- Code passes `uv run ruff check .` and `uv run ruff format --check .`.
