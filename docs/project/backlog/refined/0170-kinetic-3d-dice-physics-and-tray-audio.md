---
id: '0170'
title: Kinetic 3D Dice Physics and Tray Audio Integration
status: Refined
created: 2026-09-26
dependencies:
- TASK-0150
- TASK-0142
governing_adrs:
- ADR-0004
- ADR-0006
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0021
governing_stories:
- US-0061
target_release: 0.7.0
---

# TASK-0170: Kinetic 3D Dice Physics and Tray Audio Integration

## Status
Refined

## Summary
Integrate 3D polyhedral rigid-body dice collisions with Cannon-es physics, Three.js WebGL rendering, and synchronized WebAudio acoustic tray clatter in `services/board_state/ui/src/physics_3d/`, matching settled resting dice faces to server-side cryptographic rolls 100% reliably.

## Problem Statement
Standard digital dice rolling reduces dramatic tabletop actions to instant numbers printed in chat or simple flat 2D overlays. Stream spectators and players miss the physical anticipation, tumbling momentum, and acoustic clatter of polyhedral dice bouncing off walls, pillars, and miniature bases before settling on a critical outcome.

## Governing Architecture & ADRs
- **ADR-0004: Lit + Vite Microfrontends with Storybook**: Encapsulated WebGL canvas and WebAudio components with Shadow DOM isolation.
- **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Board and dice settled domain event notification.
- **ADR-0012: Design System Theming and Bauhaus Modernism**: Theme-reactive dice materials and high-contrast numerical face glyphs.
- **ADR-0013: Modular Microfrontend Decomposition**: Component subviews and physics modules strictly < 160 lines per module.

## Product & User Story References
- **Product Requirement**: [`prd-0021-3d-miniature-tokens-and-tabletop-physics.md`](../../product/accepted/prd-0021-3d-miniature-tokens-and-tabletop-physics.md)
- **User Story**: [`us-0061-3d-miniature-tokens-and-tabletop-physics.md`](../../user_stories/accepted/us-0061-3d-miniature-tokens-and-tabletop-physics.md) (Scenario 1: Physical Dice Collision with 3D Miniatures)

## Detailed Specification & Implementation Plan
1. **Polyhedral Rigid-Body Geometries (`services/board_state/ui/src/physics_3d/dice_models.ts`)**:
   - Parametric geometries and collision meshes for d4, d6, d8, d10, d12, and d20 dice with calibrated restitution, center of mass, and friction parameters (< 140 lines).
2. **Acoustic Tray Clatter Audio Engine (`services/board_state/ui/src/physics_3d/tray_audio.ts`)**:
   - WebAudio synthesis and foley player triggering velocity-scaled acoustic impacts on board perimeter and obstacle collision contacts (< 120 lines).
3. **Deterministic Dice Toss Solver & Cryptographic Alignment (`services/board_state/ui/src/physics_3d/dice_solver.ts`)**:
   - Trajectory and rotational momentum calculator that guarantees final resting face values conform exactly to cryptographic roll outcomes received from `services/game_session/` (< 140 lines).
4. **Storybook Interactive Showcase (`services/board_state/ui/src/runefoble-dice-tray-3d.stories.ts`)**:
   - Interactive Storybook visual stories demonstrating multi-dice throws, boundary bounces, sound triggers, and light/dark theme contrast (< 130 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Consumes completed TASK-0150 backend physics and TASK-0142 WebGL canvas without blocking core turn or combat states.
- **Negotiable (N)**: Throw velocity ranges, roll duration, and acoustic sound profiles are configurable.
- **Valuable (V)**: Restores the tactile drama, shared suspense, and auditory feedback of rolling physical dice.
- **Estimable (E)**: Builds upon Cannon-es physics meshes and existing Three.js canvas setup.
- **Small (S)**: Bounded strictly to `services/board_state/ui/src/physics_3d/`; all modules < 160 lines.
- **Testable (T)**: Frontdoor blackbox tests verify deterministic resting coordinates, roll event emission, and audio trigger invocations.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Microfrontend Architecture**:
   - Physics modules and audio synthesizer created in `services/board_state/ui/src/physics_3d/`.
   - All modules strictly < 160 lines per Hard Invariant 6.
2. **Frontdoor Test Verification**:
   - Blackbox test suite `tests/test_blackbox_3d_dice_physics/` verifies cryptographic alignment on rolls and DOM event dispatch.
3. **Quality Gates**:
   - Storybook visual demonstration renders with zero console warnings.
   - Passes `uv run pytest tests/test_blackbox_3d_dice_physics/`, `uv run ruff check .`, and `uv run ruff format --check .`.
