---
id: '0123'
title: Character Sheet Microfrontend Styles Modular Decomposition
status: Complete
created: 2026-09-26
dependencies:
- TASK-0107
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
target_release: 0.4.0
pr_url: https://github.com/tyevans/runefoble/pull/137
---
# TASK-0123: Character Sheet Microfrontend Styles Modular Decomposition

## Status
Refined

## Summary
Decompose `services/character_sheet/ui/src/runefoble-character-sheet.styles.ts` (394 lines) into discrete CSS modules (`inventory.styles.ts`, `conditions.styles.ts`, and `core.styles.ts`), keeping all style modules strictly under 200 lines.

## Problem Statement
`services/character_sheet/ui/src/runefoble-character-sheet.styles.ts` currently spans 394 lines in a single template string, approaching the 400-line warning threshold. It combines styles for equipment slots, encumbrance meters, condition badges, stat blocks, and spell slot trackers.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Bauhaus geometric tokens and CSS template composition.
- **ADR-0012: Design System Dark and Light Mode Theming**: Semantic color token invariants.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Presentation isolation within bounded context.

## Detailed Specification & Implementation Plan
1. **Core Container & Attributes (`runefoble-character-sheet.core.styles.ts`)**:
   - Base component host layout, typography, header banner, and primary stat grid (< 140 lines).
2. **Equipment & Inventory Styles (`runefoble-character-sheet.inventory.styles.ts`)**:
   - Paper doll equipment slots, slot rarity borders, item tooltips, and encumbrance bar (< 140 lines).
3. **Conditions & Spell Tracker Styles (`runefoble-character-sheet.conditions.styles.ts`)**:
   - Condition badges, absence penalty tags, spell slot pips, and responsive mobile breakpoints (< 140 lines).
4. **Style Aggregator (`runefoble-character-sheet.styles.ts`)**:
   - Aggregates and exports the modular style blocks as a combined `CSSResultGroup` (< 40 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Pure CSS refactoring without altering Lit component logic or DOM templates.
- **Negotiable (N)**: Grouping of badge vs spell slot styles can be tuned.
- **Valuable (V)**: Keeps style definitions maintainable and compliant with file length limits.
- **Estimable (E)**: Standard Lit CSS splitting into multiple `css` template literals.
- **Small (S)**: Scope strictly isolated to `services/character_sheet/ui/src/`; all files < 150 lines.
- **Testable (T)**: Verified by Storybook visual testing and frontend build.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Decomposed Style Files**:
   - `inventory.styles.ts`, `conditions.styles.ts`, and `core.styles.ts` created; each < 180 lines.
2. **Zero Visual Regressions**:
   - Storybook stories for `<runefoble-character-sheet>` render identically across light and dark modes.
3. **Quality Gates**:
   - Hard Invariant 6 met (< 500 lines per file).
   - Passes `pnpm run build` and `tests/test_blackbox_character_sheet_ui.py`.
