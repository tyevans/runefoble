---
id: '0306'
title: The Watcher Models Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0002
governing_adrs:
- ADR-0002
- ADR-0003
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0001
governing_stories:
- US-0001
- US-0003
- US-0023
target_release: 0.8.0
---

# TASK-0306: The Watcher Models Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/the_watcher/src/the_watcher/models.py` (292 lines, 58.4% of limit) into modular submodules under `services/the_watcher/src/the_watcher/models/` (`intent.py`, `stand_in.py`, `scene.py`, `copilot.py`, `faction.py`, `__init__.py`), keeping each submodule strictly < 80 lines per Hard Invariant 6.

## Problem Statement
`services/the_watcher/src/the_watcher/models.py` defines Pydantic schemas for the entire The Watcher bounded context:
1. Speech intent parsing schemas and confidence ratings.
2. AI stand-in decisions, penalty effects, and absentee recaps.
3. Procedural scene, encounter, and atmosphere generation schemas.
4. DM copilot whispers, narrative guidance, and veto structures.
5. Faction regional unrest, rivalry, and turf war models.

As conversational combat reactions, multi-party diplomacy, and advanced autonomous DM behaviors are introduced, this model definition file will exceed the 500-line limit unless decomposed.

## Governing Architecture & ADRs
- **ADR-0002: Event-Driven Watcher Architecture**: Clean model definitions for AI intent and event pipelines.
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Standard modular package structure.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation of Watcher models.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 80 lines).

## Scope of Work
1. **Intent Models Submodule (`services/the_watcher/src/the_watcher/models/intent.py`)**:
   - Extract `IntentResult`, action type validators, and confidence mappings (< 60 lines).
2. **Stand-In Models Submodule (`services/the_watcher/src/the_watcher/models/stand_in.py`)**:
   - Extract `StandInAction`, `StandInRecapResponse`, `RecapRequest` (< 60 lines).
3. **Scene & Encounter Models Submodule (`services/the_watcher/src/the_watcher/models/scene.py`)**:
   - Extract `SceneGenerateRequest`, `EncounterSpawnRequest`, `AtmosphereRequest` (< 60 lines).
4. **DM Copilot Models Submodule (`services/the_watcher/src/the_watcher/models/copilot.py`)**:
   - Extract `CopilotWhisper`, `NarrativeSuggestion`, `VetoRequest` (< 60 lines).
5. **Faction Models Submodule (`services/the_watcher/src/the_watcher/models/faction.py`)**:
   - Extract faction turf war requests, resource transfer, and bribery models (< 60 lines).
6. **Package Facade (`services/the_watcher/src/the_watcher/models/__init__.py`)**:
   - Export all models with 100% backwards compatibility (< 40 lines).
7. **Verification**:
   - Run `uv run pytest tests/test_speech_to_intent.py tests/test_autonomous_dm.py` to ensure complete compatibility.

## Definition of Done
- `services/the_watcher/src/the_watcher/models.py` replaced by `services/the_watcher/src/the_watcher/models/` package.
- All submodules strictly < 80 lines each per Hard Invariant 6.
- 100% backwards compatibility preserved for all imports from `the_watcher.models`.
- Watcher test suites pass cleanly.
