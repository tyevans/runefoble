---
id: '0178'
title: GameSession Models Modular Decomposition
status: Proposed
created: 2026-09-26
dependencies:
- TASK-0175
governing_adrs:
- ADR-0003
- ADR-0007
governing_prds: []
governing_stories: []
target_release: 0.7.0
---

# TASK-0178: GameSession Models Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/game_session/src/game_session/models.py` (382 lines, 76.4% of limit) into modular submodules under `services/game_session/src/game_session/models/` (`session.py`, `turn_order.py`, `initiative.py`, `reactions.py`, `settlement.py`), keeping all model definitions strictly < 150 lines per Hard Invariant 6.

## Problem Statement
`services/game_session/src/game_session/models.py` has grown to 382 lines as session models, combat turns, initiative mechanics, reaction states, and settlement data transfer objects have accumulated in a single file. Decomposing it into domain-focused submodules maintains maintainability and prevents file length invariant violations.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout in `services/game_session/`.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation for session and combat state schemas.

## Scope of Work
1. **Model Submodule Directory (`services/game_session/src/game_session/models/`)**:
   - `session.py`: Session configuration, participant status, and session metadata (< 100 lines).
   - `combat.py`: Initiative rolls, turn order, and round progression (< 100 lines).
   - `reactions.py`: Reaction declarations, triggers, and state enums (< 90 lines).
   - `settlement.py`: Frontier outpost and haven schemas (< 80 lines).
2. **Backwards Compatibility Facade (`services/game_session/src/game_session/models/__init__.py`)**:
   - Re-export schemas to maintain transparent imports across routers and services (< 60 lines).
3. **Verification**:
   - Verify blackbox tests and game session test suites pass cleanly.

## Definition of Done
- `services/game_session/src/game_session/models/` created with focused submodules.
- All model files strictly < 120 lines.
- All game session tests pass with `uv run pytest services/game_session/`.
- Passes `uv run ruff check .` and `uv run ruff format --check .`.
