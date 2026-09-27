---
id: '0171'
title: Miniature Knockback Impulse and Elevation Physics
status: Refined
created: 2026-09-26
dependencies:
- TASK-0150
- TASK-0142
governing_adrs:
- ADR-0004
- ADR-0006
- ADR-0011
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0021
governing_stories:
- US-0061
target_release: 0.7.0
---

# TASK-0171: Miniature Knockback Impulse and Elevation Physics

## Status
Refined

## Summary
Implement directional impulse knockback, sliding deceleration, and elevation ledge gravity falls with upright balance recovery for 3D miniature tokens in `services/board_state/ui/src/physics_3d/`, snapping final resting positions to board grid coordinates within 50ms of physics settlement.

## Problem Statement
Spell impacts, thunderwave blasts, bull rushes, and shoving attacks currently calculate coordinate updates instantaneously without kinetic momentum, sliding friction, or elevation drops. Miniatures look like static tokens blinking across cells instead of physically reacting to battlefield violence.

## Governing Architecture & ADRs
- **ADR-0004: Lit + Vite Microfrontends with Storybook**: Encapsulated WebGL canvas and physics solvers within board microfrontends.
- **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Board token displacement and collision event propagation.
- **ADR-0011: eventsource-py Core Event Sourcing**: Coordinate updates recorded via `BoardStateAggregate`.
- **ADR-0012: Design System Theming and Bauhaus Modernism**: High-contrast impulse trajectory visualizers and elevation height badges.
- **ADR-0013: Modular Microfrontend Decomposition**: Component subviews and physics solvers kept strictly < 160 lines per module.

## Product & User Story References
- **Product Requirement**: [`prd-0021-3d-miniature-tokens-and-tabletop-physics.md`](../../product/accepted/prd-0021-3d-miniature-tokens-and-tabletop-physics.md)
- **User Story**: [`us-0061-3d-miniature-tokens-and-tabletop-physics.md`](../../user_stories/accepted/us-0061-3d-miniature-tokens-and-tabletop-physics.md) (Scenario 2: Miniature Knockback and Elevation Physics)

## Detailed Specification & Implementation Plan
1. **Directional Impulse Vector Solver (`services/board_state/ui/src/physics_3d/knockback_solver.ts`)**:
   - Calculates force vectors, mass scaling, deceleration sliding friction, and obstacle collision rebounds (< 140 lines).
2. **Elevation Step & Ledge Gravity Fall (`services/board_state/ui/src/physics_3d/elevation_fall.ts`)**:
   - Raycast heightfield collision dropping miniatures down vertical elevation steps with rotational tilt damping and upright balance recovery (< 140 lines).
3. **Discrete Board Grid Snapper (`services/board_state/ui/src/physics_3d/grid_snapper.ts`)**:
   - Snaps miniature coordinates to discrete board grid centers within 50ms of physics settlement, triggering board state synchronization (< 120 lines).
4. **Storybook Interactive Showcase (`services/board_state/ui/src/runefoble-knockback-3d.stories.ts`)**:
   - Interactive Storybook visual stories demonstrating bull-rush shoves, cliff drops, wall bounces, and theme switches (< 130 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Consumes existing TASK-0150 collision engine and TASK-0142 WebGL token meshes without modifying active turn progression.
- **Negotiable (N)**: Restitution bounce coefficients and fall gravity speed can be calibrated.
- **Valuable (V)**: Gives combat impacts visceral physical weight and tactile drama.
- **Estimable (E)**: Standard rigid-body impulse math applied to existing token transforms.
- **Small (S)**: Bounded strictly to `services/board_state/ui/src/physics_3d/`; all modules < 160 lines.
- **Testable (T)**: Frontdoor blackbox tests verify knockback displacement distances, elevation drops, and grid snapping accuracy.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Microfrontend Architecture**:
   - Physics solvers and grid snapper created in `services/board_state/ui/src/physics_3d/`.
   - All modules strictly < 160 lines per Hard Invariant 6.
2. **Frontdoor Test Verification**:
   - Blackbox test suite `tests/test_blackbox_miniature_knockback/` asserts coordinate snapping, elevation changes, and DOM/WebSocket event emissions.
3. **Quality Gates**:
   - Storybook visual demonstration renders with zero console errors.
   - Passes `uv run pytest tests/test_blackbox_miniature_knockback/`, `uv run ruff check .`, and `uv run ruff format --check .`.
