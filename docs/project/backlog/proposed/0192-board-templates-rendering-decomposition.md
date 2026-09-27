---
id: '0192'
title: Board Templates Rendering and Subviews Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0004
- TASK-0084
- TASK-0125
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0013
governing_stories:
- US-0043
- US-0056
target_release: 0.7.0
---

# TASK-0192: Board Templates Rendering and Subviews Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/board_state/ui/src/board-templates.ts` (338 lines, 67.6% of limit) into modular template components under `services/board_state/ui/src/templates/` (`kinematics.template.ts`, `cell.template.ts`, `overlays.template.ts`), keeping each template module strictly < 130 lines per Hard Invariant 6.

## Problem Statement
`services/board_state/ui/src/board-templates.ts` contains 338 lines of Lit HTML templates spanning distance rulers, vector line overlays, ghost previews, grid cell rendering with health bars, header controls, radial menu overlays, and AoE template banners. As Milestone 9 adds 3D miniature controls and elevation markers, this file will soon exceed 400 lines unless modularized into focused template files.

## Governing Architecture & ADRs
- **ADR-0004: Frontend Visualizer & Lit Component Architecture**: Separation of presentation templates from component state controllers.
- **ADR-0012: Theming Tokens & Bauhaus Design System**: Consistent Bauhaus design tokens across board rendering.
- **ADR-0013: Microfrontend Bounded Context Architecture**: UI encapsulation within `services/board_state/ui/`.

## Scope of Work
1. **Modular Template Subdirectory (`services/board_state/ui/src/templates/`)**:
   - `kinematics.template.ts`: Distance ruler, vector overlay SVG, spoken ghost banner, and health bar color calculations (< 90 lines).
   - `cell.template.ts`: Tactical grid cell rendering, tokens, hazard badges, terrain, active turns, and ghost tokens (< 120 lines).
   - `overlays.template.ts`: Board header, status bar with color legend, radial action menu overlay, and AoE template banners (< 130 lines).
2. **Aggregator Facade (`services/board_state/ui/src/board-templates.ts`)**:
   - Re-export modular template renderers and interfaces to preserve full backward compatibility (< 50 lines).
3. **Verification**:
   - Verify Storybook builds and board stories render without error.
   - Verify board state blackbox tests pass cleanly.

## Definition of Done
- `services/board_state/ui/src/board-templates.ts` reduced to < 60 lines.
- Submodules in `services/board_state/ui/src/templates/` strictly < 130 lines each.
- Storybook stories and microfrontend tests pass cleanly.
