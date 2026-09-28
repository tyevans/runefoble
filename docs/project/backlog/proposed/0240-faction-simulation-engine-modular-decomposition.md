---
id: '0240'
title: Faction Simulation Engine Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0126
- TASK-0161
- TASK-0162
governing_adrs:
- ADR-0002
- ADR-0006
- ADR-0007
- ADR-0011
governing_prds:
- PRD-0017
governing_stories:
- US-0057
target_release: 0.8.0
---

# TASK-0240: Faction Simulation Engine Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/the_watcher/src/the_watcher/simulation_engine.py` (302 lines, 60.4% of limit) into modular simulation sub-modules under `services/the_watcher/src/the_watcher/simulation/` (`engine.py`, `clashes.py`, `unrest.py`), keeping each module strictly < 120 lines per Hard Invariant 6 and ADR-0002/ADR-0007.

## Problem Statement
`services/the_watcher/src/the_watcher/simulation_engine.py` currently contains 302 lines handling campaign faction tracking, world tick advancement, dice-based clash resolutions, regional unrest propagation, and intelligence bulletin generation in a single module. As faction mechanics expand, decomposing this engine into focused simulation modules improves maintainability and safeguards against invariant violations.

## Governing Architecture & ADRs
- **ADR-0002: Event-Driven Watcher Gameplay Orchestration**: Domain event sourcing for simulation ticks.
- **ADR-0006: Redis Streams Event Bus**: Event publishing across `runefoble.events.watcher` stream.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation for autonomous NPC faction simulation.
- **ADR-0011: eventsource-py Core Event Sourcing**: Handling aggregate state transitions during world ticks.

## Scope of Work
1. **Simulation Sub-Modules (`services/the_watcher/src/the_watcher/simulation/`)**:
   - `engine.py`: Core `FactionSimulationEngine` orchestration, registration, and tick lifecycle (< 110 lines).
   - `clashes.py`: Rival faction clash calculations, power shifts, and casualty evaluations (< 90 lines).
   - `unrest.py`: Regional unrest accumulation, escalation triggers, and geopolitical shift generator (< 90 lines).
2. **Aggregator Facade (`services/the_watcher/src/the_watcher/simulation_engine.py`)**:
   - Re-export `FactionSimulationEngine`, helper functions (`to_uuid`), and maintain 100% backward compatibility (< 40 lines).
3. **Verification**:
   - Run blackbox tests in `tests/test_blackbox_faction_simulation.py` and `tests/test_blackbox_turf_war.py`.
   - Verify all tests pass cleanly.

## Definition of Done
- `simulation_engine.py` decomposed into modular sub-modules strictly < 120 lines each.
- `simulation_engine.py` remains a clean facade re-exporting symbols.
- Passes `uv run pytest tests/test_blackbox_faction_simulation.py tests/test_blackbox_turf_war.py`.
- Passes `uv run ruff check .` and `uv run ruff format --check .`.
