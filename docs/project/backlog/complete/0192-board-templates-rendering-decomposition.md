---
id: 0192
title: Board Templates Rendering and Subviews Modular Decomposition
status: Complete
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
pr_url: https://github.com/tyevans/runefoble/pull/253
---
# TASK-0192: Board Templates Rendering and Subviews Modular Decomposition

## Status
Refined

## Summary
Decompose `services/board_state/ui/src/board-templates.ts` (338 lines, 67.6% of limit) into modular template components under `services/board_state/ui/src/templates/` (`kinematics.template.ts`, `cell.template.ts`, `overlays.template.ts`), keeping each template module strictly < 130 lines per Hard Invariant 6 and ADR-0013.

## Problem Statement
`services/board_state/ui/src/board-templates.ts` contains 338 lines of Lit HTML templates spanning distance rulers, vector line overlays, ghost previews, grid cell rendering with health bars, header controls, radial menu overlays, and AoE template banners in a single file. As Milestone 9 adds 3D miniature controls and elevation markers, this file will soon exceed 400 lines unless modularized into focused template files.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Clean separation of Lit presentation templates from component state controllers.
- **ADR-0012: Design System Theming and Bauhaus Modernism**: Consistent Bauhaus design tokens across board rendering.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: UI encapsulation within `services/board_state/ui/`.

## Detailed Specification & Implementation Plan
1. **Kinematics Template (`services/board_state/ui/src/templates/kinematics.template.ts`)**:
   - Distance ruler, vector overlay SVG, spoken ghost banner, and health bar color calculations (< 90 lines).
2. **Grid Cell Template (`services/board_state/ui/src/templates/cell.template.ts`)**:
   - Tactical grid cell rendering, tokens, hazard badges, terrain, active turns, and ghost tokens (< 120 lines).
3. **Overlays Template (`services/board_state/ui/src/templates/overlays.template.ts`)**:
   - Board header, status bar with color legend, radial action menu overlay, and AoE template banners (< 130 lines).
4. **Aggregator Facade (`services/board_state/ui/src/board-templates.ts`)**:
   - Re-export modular template renderers and interfaces to preserve full backward compatibility (< 50 lines).
5. **Verification**:
   - Verify Storybook builds and board stories render without error.
   - Run `uv run pytest services/board_state/ tests/test_blackbox_board*.py`.

## INVEST Criteria Evaluation
- **Independent (I)**: Template refactoring isolated strictly to `services/board_state/ui/src/templates/`.
- **Negotiable (N)**: Sub-template boundaries cleanly divide kinematics math, grid cells, and HUD overlays.
- **Valuable (V)**: Safeguards against Hard Invariant 6 (500 lines) and improves maintainability of tactical board rendering.
- **Estimable (E)**: Pure Lit template HTML refactoring preserving existing function signatures.
- **Small (S)**: Bounded strictly to `services/board_state/ui/`; all sub-templates < 130 lines.
- **Testable (T)**: Frontdoor verification through Storybook and blackbox board state tests.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Module Architecture**:
   - `services/board_state/ui/src/board-templates.ts` reduced to strictly < 60 lines.
   - Submodules in `services/board_state/ui/src/templates/` strictly < 130 lines each.
2. **Frontdoor Test Verification**:
   - `uv run pytest services/board_state/ tests/test_blackbox_board*.py` passes cleanly.
3. **Quality Gates**:
   - Storybook stories and microfrontend tests pass cleanly.
   - Code passes `uv run ruff check .` and `uv run ruff format --check .`.
