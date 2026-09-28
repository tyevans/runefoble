---
id: '0299'
title: Autonomous DM Test Suite Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0013
- TASK-0062
governing_adrs:
- ADR-0002
- ADR-0006
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0003
governing_stories:
- US-0007
- US-0012
target_release: 0.8.0
---

# TASK-0299: Autonomous DM Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_autonomous_dm.py` (296 lines, 59.2% of limit) into modular test submodules under `tests/test_autonomous_dm/` (`conftest.py`, `test_scenes.py`, `test_encounters.py`, `test_tactics.py`, `test_api.py`), keeping all test files strictly < 100 lines per Hard Invariant 6.

## Problem Statement
`tests/test_autonomous_dm.py` tests scene atmosphere generation, encounter spawning and difficulty balancing, tactical NPC combat turn decisions, CloudEvents compliance, and FastAPI endpoints all in a single 296-line file. As autonomous dungeon traps and multi-monster group tactics expand, this test suite will soon breach the 500-line invariant limit unless structured into dedicated submodules.

## Governing Architecture & ADRs
- **ADR-0002: CloudEvents 1.0 Domain Events**: Validates `SceneAtmosphereSet`, `EncounterSpawned`, and `AutonomousActionResolved` events.
- **ADR-0006: Redis Streams Event Bus Transport**: Verifies event bus publishing and mock integration.
- **ADR-0007: Domain-Driven AI DM Engine**: Validates autonomous DM presets and combat tactics.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 100 lines).

## Scope of Work
1. **Shared Fixtures (`tests/test_autonomous_dm/conftest.py`)**:
   - Extract test client setup, `AutonomousDMEngine` fixture, and event bus mocks (< 40 lines).
2. **Scene Generation Tests (`tests/test_autonomous_dm/test_scenes.py`)**:
   - Extract preset scene tests (dungeon, crypt, tavern, forest, dragon_lair) (< 80 lines).
3. **Encounter Balancing Tests (`tests/test_autonomous_dm/test_encounters.py`)**:
   - Extract encounter spawning, difficulty calculation, and monster budget assertions (< 80 lines).
4. **NPC Combat Tactics Tests (`tests/test_autonomous_dm/test_tactics.py`)**:
   - Extract tactical decision trees (lowest HP focus, spellcasting, finishing strike) (< 90 lines).
5. **REST API & CloudEvents Tests (`tests/test_autonomous_dm/test_api.py`)**:
   - Extract FastAPI endpoints and CloudEvents registry verification (< 90 lines).
6. **Verification**:
   - Safely remove monolithic `tests/test_autonomous_dm.py` and run `uv run pytest tests/test_autonomous_dm/`.

## Definition of Done
- `tests/test_autonomous_dm.py` decomposed into `tests/test_autonomous_dm/` package.
- All extracted test files strictly < 100 lines per Hard Invariant 6.
- 100% test passing via `uv run pytest tests/test_autonomous_dm/`.
- Monolithic `tests/test_autonomous_dm.py` safely removed.
