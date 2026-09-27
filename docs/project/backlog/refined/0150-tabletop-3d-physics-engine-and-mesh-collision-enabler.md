---
id: '0150'
title: Tabletop 3D Physics Engine & Mesh Collision Integration
status: Refined
created: 2026-09-26
dependencies:
- TASK-0004
- TASK-0017
- TASK-0019
- TASK-0104
governing_adrs:
- ADR-0003
- ADR-0006
- ADR-0011
governing_prds:
- PRD-0013
governing_stories:
- US-0061
target_release: 0.6.0
---

# TASK-0150: Tabletop 3D Physics Engine & Mesh Collision Integration

## Status
Refined

## Summary
Build the foundational backend physics and collision simulation engine for 3D tabletop miniatures and tumbling physical dice within `services/board_state/src/board_state/physics/`, providing rigid-body collision meshes, elevation step calculations, and spatial impact event dispatch.

## Problem Statement
While 2D board kinematics (TASK-0084) and WebGL particle VFX (TASK-0104) provide flat top-down spatial effects, upcoming Milestone 7 capabilities (3D miniatures, physical dice rolling on terrain, knockbacks against walls) require a deterministic physics simulation backend that calculates rigid-body velocities, restitution bounds, and terrain height step collisions.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout in `services/board_state/src/board_state/physics/`.
- **ADR-0006: Redis Streams Event Bus Architecture**: Publishing `board.physics.collision` and `board.dice.settled` domain events.
- **ADR-0011: eventsource-py Core Event Sourcing**: Recording physical collision impulses in `BoardStateAggregate`.

## Product & User Story References
- **Product Requirement**: [`prd-0013-immersive-and-intuitive-frontend-experience.md`](../../product/accepted/prd-0013-immersive-and-intuitive-frontend-experience.md)
- **User Story**: [`us-0061-3d-miniature-tokens-and-tabletop-physics.md`](../../user_stories/accepted/us-0061-3d-miniature-tokens-and-tabletop-physics.md)

## Detailed Specification & Implementation Plan
1. **Collision Boundaries & Shapes (`services/board_state/src/board_state/physics/bounds.py`)**:
   - Define bounding boxes, oriented bounding cylinders for tokens, and heightfield terrain collision grids (< 140 lines).
2. **Impulse & Trajectory Simulator (`services/board_state/src/board_state/physics/simulator.py`)**:
   - Compute ballistic trajectories, restitution bounces, drag, and stopping friction (< 150 lines).
3. **Physics Aggregate State Applier (`services/board_state/src/board_state/physics/applier.py`)**:
   - Handle token knockbacks and displacement collisions, ensuring tokens snap to valid grid centers upon coming to rest (< 120 lines).
4. **Frontdoor Physics Router (`services/board_state/src/board_state/routers/physics.py`)**:
   - Endpoints `POST /api/v1/boards/{board_id}/physics/simulate-throw` and `POST /api/v1/boards/{board_id}/physics/knockback` (< 130 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Foundational backend enabler that serves both 3D dice rolling and token knockback physics without frontend coupling.
- **Negotiable (N)**: Physics fidelity (simplified bounding boxes vs mesh triangles) can be tuned.
- **Valuable (V)**: Unlocks tangible 3D physics gameplay and high-fidelity streaming spectacle.
- **Estimable (E)**: Pure mathematical collision simulation with deterministic test inputs.
- **Small (S)**: Bounded strictly to `services/board_state/src/board_state/physics/`; all files < 160 lines.
- **Testable (T)**: Frontdoor blackbox tests verifying deterministic resting coordinates and collision events.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Modular Architecture**:
   - `services/board_state/src/board_state/physics/` created with `bounds.py`, `simulator.py`, `applier.py`.
   - `routers/physics.py` mounted in board state.
   - All files strictly < 180 lines.
2. **Frontdoor Blackbox Verification**:
   - `tests/test_blackbox_tabletop_physics.py` verifying:
     - Dice toss calculation returns final face and settled board coordinate.
     - Token knockback halts upon colliding with high-elevation wall.
     - Domain event `board.physics.collision` emitted with impact energy.
3. **Quality Gates**:
   - `uv run pytest tests/test_blackbox_tabletop_physics.py` passes cleanly.
   - Passes `uv run ruff check .` and `uv run ruff format --check .`.
