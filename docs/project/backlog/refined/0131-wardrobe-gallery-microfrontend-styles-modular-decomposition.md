---
id: '0131'
title: Wardrobe Gallery Microfrontend Styles and Sub-Components Modular Decomposition
status: Refined
created: 2026-09-26
dependencies:
- TASK-0124
governing_adrs:
- ADR-0004
- ADR-0009
- ADR-0012
- ADR-0013
target_release: 0.4.0
governing_prds:
- PRD-0016
governing_stories:
- US-0055
---

# TASK-0131: Wardrobe Gallery Microfrontend Styles and Sub-Components Modular Decomposition

## Status
Refined

## Summary
Decompose `services/character_sheet/ui/src/runefoble-wardrobe-gallery.ts` (401 lines, 80.2% of limit) by extracting its extensive CSS stylesheet block into a dedicated styles module `services/character_sheet/ui/src/runefoble-wardrobe-gallery.styles.ts` and isolating condition badge sub-renderers, reducing the main component to ~200 lines and maintaining strict compliance with Hard Invariant 6 (< 500 lines).

## Problem Statement
`services/character_sheet/ui/src/runefoble-wardrobe-gallery.ts` currently spans 401 lines following the implementation of TASK-0124. Over 180 lines of this file consist of inline CSS custom property definitions, grid layouts, and avatar state styling (`static styles = css...`). As additional wardrobe tags, emotion indicators, and filter controls are added, this file is approaching the 500-line invariant limit.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Strict Shadow DOM encapsulation and modular CSS styles separation.
- **ADR-0009: Bauhaus Modernist Design System**: Semantic tokens and CSS variables.
- **ADR-0012: Dark/Light Mode Theming System**: Theme variables and contrast compliance.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Service-owned component styling in `services/character_sheet/ui/src/`.

## Product & User Story References
- **Product Requirement**: [`prd-0016-character-leitmotifs-and-kinetic-spell-vfx.md`](../../product/accepted/prd-0016-character-leitmotifs-and-kinetic-spell-vfx.md)
- **User Story**: [`us-0055-dynamic-character-wardrobe-and-condition-portraits.md`](../../user_stories/accepted/us-0055-dynamic-character-wardrobe-and-condition-portraits.md)

## Detailed Specification & Implementation Plan
1. **Style Module Extraction (`services/character_sheet/ui/src/runefoble-wardrobe-gallery.styles.ts`)**:
   - Extract `static styles` into an exported `wardrobeGalleryStyles` CSSResult module (< 190 lines).
2. **Main Component Streamlining (`services/character_sheet/ui/src/runefoble-wardrobe-gallery.ts`)**:
   - Refactor component to import external styles, keeping rendering and event dispatch logic isolated (< 220 lines).
3. **Blackbox & Storybook Verification**:
   - Verify zero visual or functional regressions in Storybook stories and blackbox tests.

## INVEST Criteria Evaluation
- **Independent (I)**: Pure UI styling and template refactoring without modifying backend REST endpoints or domain events.
- **Negotiable (N)**: Style token organization and sub-renderer granularity can be adjusted.
- **Valuable (V)**: Protects codebase health against invariant breaches and enhances UI component maintainability.
- **Estimable (E)**: Direct CSS extraction following established patterns (e.g., `runefoble-character-sheet.styles.ts`).
- **Small (S)**: Scope strictly isolated to `services/character_sheet/ui/src/`; all resulting files < 250 lines.
- **Testable (T)**: Verified by `pnpm run build` and `uv run pytest tests/test_blackbox_wardrobe_gallery.py`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Modular Styles**:
   - `services/character_sheet/ui/src/runefoble-wardrobe-gallery.styles.ts` created and imported cleanly.
2. **Line Count Invariant**:
   - Both `runefoble-wardrobe-gallery.ts` and `runefoble-wardrobe-gallery.styles.ts` strictly < 250 lines.
3. **Zero Regressions**:
   - 100% of existing wardrobe gallery tests and Storybook stories render without errors.
4. **Quality Gates**:
   - Conforms to Hard Invariant 6 (< 500 lines per file).
   - Passes `pnpm run build` and `uv run pytest tests/test_blackbox_wardrobe_gallery.py`.
