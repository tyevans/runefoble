---
id: '0138'
title: Board State Models and Pydantic Schemas Modular Decomposition
status: Refined
created: 2026-09-26
dependencies:
- TASK-0085
- TASK-0133
governing_adrs:
- ADR-0003
- ADR-0011
governing_prds:
- PRD-0003
- PRD-0013
governing_stories:
- US-0012
- US-0043
target_release: 0.4.0
---

# TASK-0138: Board State Models and Pydantic Schemas Modular Decomposition

## Status
Refined

## Summary
Decompose `services/board_state/src/board_state/models.py` (433 lines, 86.6% of limit) into modular, single-responsibility Pydantic schema modules under `services/board_state/src/board_state/models/` (`terrain.py`, `tokens.py`, `vfx.py`, `actions.py`, `board.py`) with facade re-exports in `models.py`, preventing future breaches of Hard Invariant 6 (< 500 lines per file).

## Problem Statement
`services/board_state/src/board_state/models.py` currently consolidates all request and response DTOs, terrain cell states, token geometries, spell casting parameters, and UVTT map import structures across 433 lines. With ongoing additions to mobile haptic ping handling and cross-campaign spatial mapping, this file will soon cross the 500-line hard invariant ceiling.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout within `services/board_state/`.
- **ADR-0011: eventsource-py Core Event Sourcing**: DTO separation preserving clean typing for domain aggregates and REST routers.

## Product & User Story References
- **Product Requirements**:
  - [`prd-0003-spatial-fog-of-war-and-visibility-engine.md`](../../product/accepted/prd-0003-spatial-fog-of-war-and-visibility-engine.md)
  - [`prd-0013-immersive-and-intuitive-frontend-experience.md`](../../product/accepted/prd-0013-immersive-and-intuitive-frontend-experience.md)
- **User Stories**:
  - [`us-0012-spatial-line-of-sight-and-fog-of-war.md`](../../user_stories/accepted/us-0012-spatial-line-of-sight-and-fog-of-war.md)
  - [`us-0043-tactile-kinetic-board-and-spoken-ghost-previews.md`](../../user_stories/accepted/us-0043-tactile-kinetic-board-and-spoken-ghost-previews.md)

## Detailed Specification & Implementation Plan
1. **Terrain & Grid Schemas (`services/board_state/src/board_state/models/terrain.py`)**:
   - Extract `TerrainCellState`, `TerrainDict`, `ConfigureTerrainRequest`, and `VisibilityResponse` (< 100 lines).
2. **Token & Placement Schemas (`services/board_state/src/board_state/models/tokens.py`)**:
   - Extract `PlacedTokenState`, `PlaceTokenRequest`, `MoveTokenRequest`, and `MoveTokenResponse` (< 100 lines).
3. **VFX & Decal Schemas (`services/board_state/src/board_state/models/vfx.py`)**:
   - Extract `BoardDecalState`, `CastSpellRequest`, `CastSpellResponse`, `FinishVFXRequest`, and `DecayDecalsRequest` (< 100 lines).
4. **Board Aggregate Schemas (`services/board_state/src/board_state/models/board.py`)**:
   - Extract `BoardState`, `CreateBoardRequest`, and `FogOfWarUpdateRequest` (< 100 lines).
5. **Facade Re-exports (`services/board_state/src/board_state/models.py`)**:
   - Re-export all schemas in `__all__` maintaining 100% backwards compatibility for callers.

## INVEST Criteria Evaluation
- **Independent (I)**: Internal refactoring with zero breaking changes to public endpoints, schemas, or tests.
- **Negotiable (N)**: Submodule grouping can be adjusted as needed.
- **Valuable (V)**: Protects against Hard Invariant 6 violation while improving codebase maintainability.
- **Estimable (E)**: Standard Python Pydantic module decomposition.
- **Small (S)**: Bounded strictly to `services/board_state/src/board_state/models.py`; each file < 120 lines.
- **Testable (T)**: Verified by existing full test suite passing with zero regressions.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Modular Architecture**:
   - Submodules created under `services/board_state/src/board_state/models/`.
   - `services/board_state/src/board_state/models.py` reduced to < 80 lines facade re-export.
2. **Line Count Invariant**:
   - Zero files exceeding 200 lines within the package.
3. **Test Suite Verification**:
   - `uv run pytest tests/test_blackbox_board_state.py tests/test_blackbox_tactile_board.py` passes.
4. **Quality Gates**:
   - Passes `uv run ruff check .` and `uv run ruff format --check .`.
