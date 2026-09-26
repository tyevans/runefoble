---
id: '0120'
title: CSS Design Tokens and Theme Variables Modular Decomposition
status: Complete
created: 2026-09-26
dependencies:
- TASK-0012
- TASK-0074
governing_adrs:
- ADR-0004
- ADR-0009
- ADR-0012
target_release: 0.3.0
governing_prds:
- PRD-0013
governing_stories:
- US-0016
- US-0041
- US-0042
pr_url: https://github.com/tyevans/runefoble/pull/123
---
# TASK-0120: CSS Design Tokens and Theme Variables Modular Decomposition

## Status
Refined

## Summary
Decompose `frontend/src/styles/themes.css` (424 lines, 84.8% of limit) into modular CSS sub-modules (`themes/base.css`, `themes/bauhaus.css`, `themes/dark-fantasy.css`, `themes/parchment.css`, `themes/cyber-rune.css`) to prevent violating Hard Invariant 6 (File length limit < 500 lines) as new broadcast themes and high-contrast accessibility tokens are added.

## Problem Statement
`frontend/src/styles/themes.css` currently aggregates all design system token definitions into a single 424-line stylesheet:
1. Universal root CSS custom properties (`--rf-font-*`, `--rf-radius-*`, `--rf-space-*`, `--rf-transition-*`).
2. Modernist Bauhaus primary geometric theme tokens across light and dark color modes.
3. Dark Fantasy gothic stone, blood crimson, and obsidian shadow tokens.
4. Parchment manuscript warm sepia, aged leather, and iron gall ink tokens.
5. Cyber-Rune neon cyan, grid wireframe, and ultraviolet tokens.

As Milestone 5 and 6 introduce spectator broadcast themes and customizable campaign colorways, this stylesheet will exceed 500 lines unless partitioned into modular partials.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Design token sharing and Storybook preview imports.
- **ADR-0009: Bauhaus Modernist Design System**: Primary color hierarchy and geometric aesthetic tokens.
- **ADR-0012: Dark/Light Mode Theming System**: Decoupled mode-independent color tokens and WCAG 2.1 AA contrast invariants.

## Product & User Story References
- **Product Requirement**: [`prd-0013-immersive-and-intuitive-frontend-experience.md`](../../product/accepted/prd-0013-immersive-and-intuitive-frontend-experience.md)
- **User Story**: [`us-0041-settings-modal-and-appearance-mode-switching.md`](../../user_stories/accepted/us-0041-settings-modal-and-appearance-mode-switching.md)

## Detailed Specification & Implementation Plan
1. **Base Tokens (`frontend/src/styles/themes/base.css`)**:
   - Universal radii, typography, spacing scales, z-indexes, and transition curves (< 90 lines).
2. **Bauhaus Theme (`frontend/src/styles/themes/bauhaus.css`)**:
   - Primary Bauhaus palettes, contrast borders, and light/dark mode variables (< 90 lines).
3. **Dark Fantasy Theme (`frontend/src/styles/themes/dark-fantasy.css`)**:
   - Gothic stone, blood crimson, and obsidian shadow palettes (< 90 lines).
4. **Parchment Theme (`frontend/src/styles/themes/parchment.css`)**:
   - Weathered paper, warm sepia, and illuminated manuscript tokens (< 90 lines).
5. **Cyber-Rune Theme (`frontend/src/styles/themes/cyber-rune.css`)**:
   - Neon cyan, ultraviolet, and dark circuitry tokens (< 90 lines).
6. **Themes Root Bundle (`frontend/src/styles/themes.css`)**:
   - Clean root stylesheet importing all theme sub-modules via standard CSS `@import` rules (< 40 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors CSS token structure without altering variable names, computed styles, or component bindings.
- **Negotiable (N)**: File naming and grouping within `frontend/src/styles/themes/`.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (< 500 lines) and enables clean additions of new themes.
- **Estimable (E)**: Clean CSS variable partitioning.
- **Small (S)**: Scope strictly isolated to `frontend/src/styles/`; all resulting files < 120 lines.
- **Testable (T)**: Verified with `uv run pytest tests/test_theming.py` and Vite build check.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Decomposition Executed**:
   - `frontend/src/styles/themes.css` decomposed into modular theme CSS files under `frontend/src/styles/themes/`.
2. **Strict Line Limit**:
   - All CSS stylesheets strictly under 150 lines in compliance with Hard Invariant 6.
3. **Full Backward Compatibility**:
   - All `--rf-*` CSS custom properties remain identical in name and computed value.
4. **Frontdoor Test Verification**:
   - All tests pass via `uv run pytest tests/test_theming.py` and `pnpm run build` in `frontend/`.
