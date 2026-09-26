---
id: '0062'
title: Autonomous DM Presets, Monster Templates, and Combat Tactics Modular Decomposition
status: Proposed
created: 2026-09-26
dependencies: [TASK-0013]
governing_adrs: [ADR-0003]
target_release: 0.2.0
---

# TASK-0062: Autonomous DM Presets, Monster Templates, and Combat Tactics Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/the_watcher/src/the_watcher/autonomous_dm.py` (387 lines, 77.4% of limit) into modular, single-responsibility domain submodules (`presets.py`, `encounters.py`, `tactics.py`) to prevent breaching Hard Invariant 6 (File length limit < 500 lines) as narrative scene presets, monster archetypes, and combat heuristics expand.

## Problem Statement
`services/the_watcher/src/the_watcher/autonomous_dm.py` bundles three distinct responsibilities in a single 387-line module:
1. Static narrative scene catalogs and atmosphere descriptions (`SCENE_PRESETS`, dungeon/crypt/tavern/forest/dragon lair lighting, moods, and ambient audio prompts).
2. Encounter balancing logic, party-level Challenge Rating (CR) scaling, and monster stat block templates across easy/medium/hard/deadly threat levels (`spawn_encounter`).
3. NPC and monster tactical decision trees, spellcaster prioritization, wounded target finishing heuristics, and combat action resolution (`resolve_npc_turn`).

As upcoming Milestone 3 features introduce procedural encounter generation, lore-informed monster rosters, and dynamic tactics, this file will quickly breach the 500-line invariant.

## Proposed Decomposition
1. **Scene Presets (`services/the_watcher/src/the_watcher/presets.py`)**:
   - Extract `SCENE_PRESETS` dictionary and scene atmosphere resolution helpers (< 90 lines).
2. **Encounter Generation (`services/the_watcher/src/the_watcher/encounters.py`)**:
   - Extract monster stat block catalogs, CR calculation, tactical objectives, and `spawn_encounter` implementation (< 140 lines).
3. **Tactical Action Resolution (`services/the_watcher/src/the_watcher/tactics.py`)**:
   - Extract target selection, spellcaster decision logic, finishing strikes, and `resolve_npc_turn` implementation (< 110 lines).
4. **Engine Facade (`services/the_watcher/src/the_watcher/autonomous_dm.py`)**:
   - Retain `AutonomousDMEngine` class as an orchestrator delegating to the submodules, maintaining 100% backward-compatible public methods (< 90 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors internal service implementation without modifying domain event schemas (`SceneAtmosphereSet`, `EncounterSpawned`, `AutonomousActionResolved`) or public HTTP endpoints.
- **Negotiable (N)**: Submodule naming and helper boundaries can be adjusted during implementation.
- **Valuable (V)**: Protects against file length limit violations (Hard Invariant 6) while making monster templates and tactics independently extensible.
- **Estimable (E)**: Pure extraction of discrete static dictionaries and methods into focused modules.
- **Small (S)**: Scope strictly isolated to `services/the_watcher/src/the_watcher/`; all resulting files < 150 lines.
- **Testable (T)**: Existing test suites (`tests/test_autonomous_dm.py`) verify 100% identical outputs and event structures.

## Acceptance Criteria
1. Re-exports and facade in `autonomous_dm.py` ensure zero breaking changes to `AutonomousDMEngine` public methods.
2. All modified and new files strictly under 180 lines.
3. 100% test pass rate on `uv run pytest tests/test_autonomous_dm.py`.
4. Conforms strictly to Hard Invariant 6 (< 500 lines per file).
