---
id: '0133'
title: Board State Aggregate Mutation Handlers and Event Appliers Modular Decomposition
status: Refined
created: 2026-09-26
dependencies:
- TASK-0008
- TASK-0017
- TASK-0054
- TASK-0104
governing_adrs:
- ADR-0003
- ADR-0006
- ADR-0011
target_release: 0.4.0
governing_prds:
- PRD-0003
- PRD-0016
governing_stories:
- US-0012
- US-0043
- US-0048
---

# TASK-0133: Board State Aggregate Mutation Handlers and Event Appliers Modular Decomposition

## Status
Refined

## Summary
Decompose `services/board_state/src/board_state/aggregate.py` (488 lines, 97.6% of limit) into modular command mutation handlers and `@handles` event state appliers under `services/board_state/src/board_state/handlers/`, reducing the main aggregate coordinator to < 140 lines and safeguarding against breaches of Hard Invariant 6 (< 500 lines).

## Problem Statement
`services/board_state/src/board_state/aggregate.py` currently defines the `BoardAggregate` class spanning 488 lines. It encapsulates all domain commands and `@handles` event reducers for:
1. Grid initialization and Universal VTT map geometry (`BoardGridInitialized`, `UniversalVTTImported`).
2. Token lifecycle, spatial coordinate validation, tactile movement, and path hazard detection (`TokenPlaced`, `TokenMoved`, `TokenHazardTriggered`, `TokenRemoved`).
3. Spatial line-of-sight and fog-of-war visibility (`FogOfWarRevealed`, `FogOfWarShrouded`).
4. Kinetic spell VFX animations, area-of-effect templates, and ephemeral decals (`SpellCast`, `AreaEffectExploded`, `VFXAnimationFinished`, `EphemeralDecalsDecayed`).

At 488 lines, any addition of radial token actions (TASK-0125) or companion haptics will immediately breach Hard Invariant 6.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout within `services/board_state/`.
- **ADR-0006: Redis Streams Event Bus**: Event dispatch alignment for board mutations and spell effects.
- **ADR-0011: eventsource-py Core Event Sourcing**: Event-sourced aggregate state management and `@handles` pattern.

## Product & User Story References
- **Product Requirement**: [`prd-0003-spatial-fog-of-war-and-visibility-engine.md`](../../product/accepted/prd-0003-spatial-fog-of-war-and-visibility-engine.md), [`prd-0016-character-leitmotifs-and-kinetic-spell-vfx.md`](../../product/accepted/prd-0016-character-leitmotifs-and-kinetic-spell-vfx.md)
- **User Stories**:
  - [`us-0012-spatial-line-of-sight-and-fog-of-war.md`](../../user_stories/accepted/us-0012-spatial-line-of-sight-and-fog-of-war.md)
  - [`us-0043-tactile-kinetic-board-and-spoken-ghost-previews.md`](../../user_stories/accepted/us-0043-tactile-kinetic-board-and-spoken-ghost-previews.md)
  - [`us-0048-kinetic-spell-vfx-and-particle-canvas.md`](../../user_stories/accepted/us-0048-kinetic-spell-vfx-and-particle-canvas.md)

## Detailed Specification & Implementation Plan
1. **Token & Grid Mutation Handlers (`services/board_state/src/board_state/handlers/tokens.py`)**:
   - Extract token placement, removal, tactile movement pathing, and hazard triggers (< 140 lines).
2. **Fog & Visibility Handlers (`services/board_state/src/board_state/handlers/fog.py`)**:
   - Extract fog-of-war revealing, shrouding, and party visibility calculations (< 120 lines).
3. **Spell VFX & Decal Handlers (`services/board_state/src/board_state/handlers/vfx.py`)**:
   - Extract AoE template explosion, spell casting, animation state completion, and ephemeral decal decay (< 120 lines).
4. **Aggregate Coordinator Facade (`services/board_state/src/board_state/aggregate.py`)**:
   - Re-export and coordinate handlers via `BoardAggregate` subclassing `DeclarativeAggregate[BoardState]` (< 140 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Internal bounded context refactoring with zero breaking changes to public events, REST endpoints, or WebSockets.
- **Negotiable (N)**: Sub-module division can be tuned during implementation.
- **Valuable (V)**: Protects core tactical combat engine from exceeding Hard Invariant 6 (488 lines currently).
- **Estimable (E)**: Directly mirrors successful decomposition performed in `TASK-0113` for `CharacterAggregate`.
- **Small (S)**: Refactoring bounded to `services/board_state/src/board_state/` with all resulting files < 150 lines.
- **Testable (T)**: Validated against comprehensive existing blackbox tests with 100% pass rate.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Modular Architecture**:
   - `services/board_state/src/board_state/handlers/` package created containing `tokens.py`, `fog.py`, and `vfx.py`.
2. **Line Count Invariant**:
   - `services/board_state/src/board_state/aggregate.py` reduced to < 150 lines.
   - All handler sub-modules strictly < 160 lines.
3. **Backwards Compatibility & Zero Regression**:
   - All public methods, properties, and `@handles` registrations on `BoardAggregate` remain identical.
4. **Verification Gates**:
   - `uv run pytest tests/test_board_state.py tests/test_blackbox_spell_vfx.py tests/test_blackbox_tactile_board.py` passes 100%.
   - `python3 scripts/health_check.py` passes with zero invariant breaches.
