---
id: '0142'
title: 3D Miniature Tokens & WebGL Tabletop Physics
status: Refined
created: 2026-09-26
dependencies:
- TASK-0004
- TASK-0017
- TASK-0104
- TASK-0150
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0013
- PRD-0021
governing_stories:
- US-0061
target_release: 0.6.0
---

# TASK-0142: 3D Miniature Tokens & WebGL Tabletop Physics

## Status
Refined

## Summary
Introduce 3D WebGL miniature tokens with physical dice rolling and terrain collision physics on the tactical board within `services/board_state/ui/src/`, allowing tokens and tumbling dice to interact with walls, pillars, and elevation changes.

## Problem Statement
While 2D board kinematics (TASK-0084) and WebGL particle VFX (TASK-0104) provide rich visual feedback, streamers and players desire tactile 3D miniatures that react to physical impacts, knockbacks, and bouncing physical dice. With backend 3D physics established in TASK-0150, client-side WebGL miniature rendering is ready to integrate.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Encapsulated Three.js WebGL canvas wrapper in `services/board_state/ui/src/`.
- **ADR-0012: Theming System and Accessibility Contrast Invariants**: Contrast rings and theme-aware lighting models.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Web component vendored in `services/board_state/ui/`.

## Product & User Story References
- **Product Requirement**: [`prd-0021-3d-miniature-tokens-and-tabletop-physics.md`](../../product/accepted/prd-0021-3d-miniature-tokens-and-tabletop-physics.md)
- **User Story**: [`us-0061-3d-miniature-tokens-and-tabletop-physics.md`](../../user_stories/accepted/us-0061-3d-miniature-tokens-and-tabletop-physics.md)

## Detailed Specification & Implementation Plan
1. **3D Miniature Token Mesh Generator (`services/board_state/ui/src/physics_3d/miniature_mesh.ts`)**:
   - Extrude 2D circular tokens into stylized 3D miniature bases with character portraits and status rings (< 180 lines).
2. **Tabletop Physics Visualizer (`services/board_state/ui/src/physics_3d/tabletop_canvas.ts`)**:
   - Three.js WebGL canvas rendering rolling dice, token meshes, and elevation cliffs (< 180 lines).
3. **Collision & Impulse Bridge (`services/board_state/ui/src/physics_3d/physics_bridge.ts`)**:
   - Bridge client state with backend physics impulse calculation and board WebSocket sync (< 140 lines).
4. **Storybook Stories (`services/board_state/ui/src/runefoble-board-3d.stories.ts`)**:
   - Stories showcasing 3D dice tumbling, token knockback, and elevation step collision.
5. **Component Export (`services/board_state/ui/src/runefoble-board.ts`)**:
   - Integrate 3D toggle layer in tactical board microfrontend.

## INVEST Criteria Evaluation
- **Independent (I)**: Builds on top of completed TASK-0150 physics engine via standard board coordinates.
- **Negotiable (N)**: Shading complexity and camera angle limits can be tuned.
- **Valuable (V)**: Elevates immersion with tangible miniature physics and tumbling dice.
- **Estimable (E)**: Three.js mesh generation mapped to existing board coordinate systems.
- **Small (S)**: Bounded strictly to `services/board_state/ui/src/physics_3d/`; all files < 180 lines.
- **Testable (T)**: Storybook stories verify visual rendering and frontdoor blackbox tests verify API manifests.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Microfrontend Architecture**:
   - 3D miniature canvas integrated into `services/board_state/ui/`.
   - All source and style files strictly < 190 lines.
2. **Storybook & Frontdoor Test Verification**:
   - Storybook stories render without console errors across both Dark and Light themes.
   - Frontdoor tests verify board state manifestation and microfrontend delivery.
3. **Quality Gates**:
   - Passes `uv run pytest tests/test_blackbox_board_state/` and frontend build verification.
