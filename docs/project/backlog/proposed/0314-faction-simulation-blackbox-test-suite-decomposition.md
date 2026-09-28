---
id: '0314'
title: Faction Simulation Blackbox Test Suite Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0126
governing_adrs:
- ADR-0002
- ADR-0006
- ADR-0011
- ADR-0013
governing_prds:
- PRD-0017
governing_stories:
- US-0057
target_release: 0.8.0
---

# TASK-0314: Faction Simulation Blackbox Test Suite Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_blackbox_faction_simulation.py` (295 lines, 59% of limit) into modular test sub-suites under `tests/test_blackbox_faction_simulation/` (`conftest.py`, `test_faction_lifecycle.py`, `test_agenda_ticks.py`, `test_conflict_and_shifts.py`), keeping each test file strictly < 130 lines per Hard Invariant 6.

## Problem Statement
`tests/test_blackbox_faction_simulation.py` covers autonomous NPC faction creation, agenda initialization, world tick resolution, conflict roll calculations, and geopolitical shift event emissions in a single 295-line file. As faction bribery, espionage rings, and territory control expansions are added, this test suite will rapidly breach the 500-line ceiling unless partitioned.

## Governing Architecture & ADRs
- **ADR-0002: Event-Driven Watcher Gameplay Orchestration**: Watcher autonomous background simulation.
- **ADR-0006: Redis Streams Event Bus**: Event dispatch and consumer testing.
- **ADR-0011: eventsource-py Core Event Sourcing**: Event-sourced aggregates and state verification.
- **ADR-0013: Modular Decomposition**: All test modules kept strictly < 500 lines (submodules < 130 lines).

## Scope of Work
1. **Fixtures & Clean Environment (`tests/test_blackbox_faction_simulation/conftest.py`)**:
   - Aggregate repositories, mock Redis bus, and clean simulation environment setup (< 60 lines).
2. **Faction Lifecycle Suite (`tests/test_blackbox_faction_simulation/test_faction_lifecycle.py`)**:
   - Faction creation, goal registration, and aggregate state restoration tests (< 90 lines).
3. **Agenda & World Ticks Suite (`tests/test_blackbox_faction_simulation/test_agenda_ticks.py`)**:
   - World tick execution, agenda progress advancement, and event publishing (< 100 lines).
4. **Conflicts & Shifts Suite (`tests/test_blackbox_faction_simulation/test_conflict_and_shifts.py`)**:
   - Faction rivalry clash resolution, power shifts, and GeopoliticalShiftOccurred events (< 110 lines).
5. **Verification**:
   - Run `uv run pytest tests/test_blackbox_faction_simulation/` to confirm all tests pass.

## Definition of Done
- `tests/test_blackbox_faction_simulation.py` decomposed into `tests/test_blackbox_faction_simulation/` package.
- All extracted test modules strictly < 130 lines each per Hard Invariant 6.
- 100% test pass rate preserved without regressions.
