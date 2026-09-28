---
id: '0309'
title: Game Session Minigames Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0103
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0014
governing_stories:
- US-0047
target_release: 0.8.0
---

# TASK-0309: Game Session Minigames Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/game_session/src/game_session/minigames.py` (291 lines, 58.2% of limit) into modular submodules under `services/game_session/src/game_session/minigames/` (`state.py`, `aggregate.py`, `__init__.py`), keeping each submodule strictly < 150 lines per Hard Invariant 6.

## Problem Statement
`services/game_session/src/game_session/minigames.py` defines both `TavernGameState` and `TavernGameAggregate` with comprehensive event handlers for minigame lifecycle (`MinigameStarted`, `MinigameTurnTaken`, `IntoxicationLevelChanged`, `MinigameEnded`) and command execution (Liar's Dice bidding, challenge resolution, drink consumption, DSP filter application) in a single 291-line file. As casino minigames (Roulette, Dragon's Ante) and spectator betting are integrated, this file will exceed 500 lines unless decoupled into separate state and aggregate modules.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout within the `game_session` service.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain aggregate decoupling.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 150 lines).

## Scope of Work
1. **Minigame State Submodule (`services/game_session/src/game_session/minigames/state.py`)**:
   - Extract `TavernGameState` with Pydantic model fields, defaults, and serializable history helpers (< 80 lines).
2. **Minigame Aggregate Submodule (`services/game_session/src/game_session/minigames/aggregate.py`)**:
   - Extract `TavernGameAggregate` with `@handles` methods and mutation methods (< 150 lines).
3. **Package Facade (`services/game_session/src/game_session/minigames/__init__.py`)**:
   - Export `TavernGameState` and `TavernGameAggregate` with 100% backwards compatibility (< 30 lines).
4. **Verification**:
   - Run `uv run pytest tests/test_blackbox_tavern_and_haggling.py` to confirm zero regression.

## Definition of Done
- `services/game_session/src/game_session/minigames.py` replaced by `services/game_session/src/game_session/minigames/` package.
- All extracted submodules strictly < 150 lines each per Hard Invariant 6.
- 100% backwards compatibility preserved for all imports from `game_session.minigames`.
- Minigame tests pass cleanly.
