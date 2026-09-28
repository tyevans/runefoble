---
id: '0201'
title: Board State Radial Menu Glyphs and Styles Modular Decomposition
status: Complete
created: 2026-09-27
dependencies:
- TASK-0125
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0013
governing_stories:
- US-0056
target_release: 0.7.0
pr_url: https://github.com/tyevans/runefoble/pull/264
---
# TASK-0201: Board State Radial Menu Glyphs and Styles Modular Decomposition

## Status
Refined

## Summary
Decompose `services/board_state/ui/src/radial_menu.ts` (321 lines, 64.2% of limit) into modular submodules under `services/board_state/ui/src/radial/` (`radial_menu.styles.ts`, `radial_glyphs.ts`, and `radial_wedge.ts`), keeping each module strictly < 110 lines per Hard Invariant 6 and ADR-0004/ADR-0013.

## Problem Statement
`services/board_state/ui/src/radial_menu.ts` spans 321 lines combining Bauhaus CSS styles (`static styles`), SVG geometric glyph generators (`renderBauhausGlyph`), polar trigonometry calculations for arc wedges (`renderWedge`), and the Lit component lifecycle. As additional quick actions (such as shove, hide, help, or grapple) are added, this file will rapidly approach the 400-line threshold unless modularized.

## Governing Architecture & ADRs
- **ADR-0004: Frontend Visualizer & Lit Component Architecture**: Separation of presentation templates, SVG glyphs, and component controllers.
- **ADR-0012: Theming Tokens & Bauhaus Design System**: Bauhaus geometric iconography and styling token isolation.
- **ADR-0013: Microfrontend Bounded Context Architecture**: UI encapsulation within `services/board_state/ui/`.

## Detailed Specification & Implementation Plan
1. **Modular Submodules (`services/board_state/ui/src/radial/`)**:
   - `radial_menu.styles.ts`: Lit CSS styles for circular radial overlay, wedge transitions, and action badges (< 90 lines).
   - `radial_glyphs.ts`: Bauhaus SVG glyph rendering functions for attack, dash, disengage, dodge, cast, etc. (< 100 lines).
   - `radial_wedge.ts`: Polar coordinate math, SVG path generator (`polarToCartesian`, `describeArc`), and wedge click handlers (< 90 lines).
2. **Component Controller Refactoring (`services/board_state/ui/src/radial_menu.ts`)**:
   - Component controller importing styles, glyphs, and wedge rendering (< 100 lines).
3. **Verification**:
   - Verify Storybook stories for `<runefoble-radial-menu>` render and respond to wedge clicks.
   - Run existing board state tests to verify zero regressions.

## INVEST Criteria Evaluation
- **Independent (I)**: Isolated entirely within `services/board_state/ui/src/` presentation components.
- **Negotiable (N)**: Clear structural separation of CSS styles, SVG glyph drawings, and trigonometric wedge math.
- **Valuable (V)**: Protects against Hard Invariant 6 and makes radial action glyphs reusable across HUD elements.
- **Estimable (E)**: Discrete extraction of independent pure rendering and math routines.
- **Small (S)**: Scope strictly isolated to `radial_menu.ts` decomposition (< 110 lines per module).
- **Testable (T)**: Frontdoor validation via Storybook stories and blackbox tactile board tests.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Module Architecture**:
   - `radial_menu.ts` reduced to strictly < 110 lines.
   - Submodules in `services/board_state/ui/src/radial/` strictly < 110 lines each.
2. **Frontdoor Verification**:
   - Storybook stories render and interactive wedge clicks fire expected custom events.
   - Microfrontend bundle builds cleanly via `pnpm run build`.
3. **Quality Gates**:
   - Code passes `uv run ruff check .` and `uv run ruff format --check .`.
