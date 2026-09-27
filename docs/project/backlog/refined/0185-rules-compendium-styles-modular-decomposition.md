---
id: '0185'
title: Rules Compendium Styles Modular Decomposition
status: Refined
created: 2026-09-27
dependencies:
- TASK-0048
- TASK-0108
governing_adrs:
- ADR-0003
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0008
governing_stories:
- US-0037
- US-0052
target_release: 0.7.0
---

# TASK-0185: Rules Compendium Styles Modular Decomposition

## Status
Refined

## Summary
Decompose `services/rules_compendium/ui/src/runefoble-rules-compendium.styles.ts` (357 lines, 71.4% of limit) by extracting encounter builder styles, homebrew form styles, and search filter styles into modular sub-stylesheets under `services/rules_compendium/ui/src/styles/`, keeping all style modules strictly < 150 lines per Hard Invariant 6 and ADR-0013.

## Problem Statement
`services/rules_compendium/ui/src/runefoble-rules-compendium.styles.ts` contains all CSS Lit tagged template literals for the compendium search view, filter tabs, monster stat blocks, homebrew creation forms, and CR encounter calculator. At 357 lines, it approaches the 400-line threshold and will breach the 500-line invariant as new encounter filters and homebrew mechanics are added unless decomposed into focused, single-responsibility CSS modules.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean modular package structure across the repository.
- **ADR-0012: Design System Theming and Bauhaus Modernism**: Tokenized CSS custom properties and theme contrast invariants.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Encapsulated component styles within service UI packages.

## Detailed Specification & Implementation Plan
1. **Base & Layout Styles (`services/rules_compendium/ui/src/styles/compendium-base.styles.ts`)**:
   - Extract search bar, filter tabs, navigation pills, and header layout (< 100 lines).
2. **Encounter Builder Styles (`services/rules_compendium/ui/src/styles/encounter-builder.styles.ts`)**:
   - Extract encounter difficulty meter, monster badge tags, and party CR thresholds (< 120 lines).
3. **Homebrew Form Styles (`services/rules_compendium/ui/src/styles/homebrew-form.styles.ts`)**:
   - Extract form inputs, stat block preview grids, and action button groups (< 110 lines).
4. **Aggregator Facade (`services/rules_compendium/ui/src/runefoble-rules-compendium.styles.ts`)**:
   - Aggregate sub-stylesheets into exported `compendiumStyles` array (< 60 lines), ensuring full backward compatibility.
5. **Verification**:
   - Verify Storybook stories render without visual regression.
   - Run tests via `uv run pytest tests/test_blackbox_rules_compendium_ui.py`.

## INVEST Criteria Evaluation
- **Independent (I)**: Style refactoring isolated strictly within `services/rules_compendium/ui/src/styles/`.
- **Negotiable (N)**: CSS module boundaries (base, encounter builder, homebrew form) group cleanly by bounded UI contexts.
- **Valuable (V)**: Safeguards against Hard Invariant 6 (500 lines) and improves modularity of design tokens.
- **Estimable (E)**: Pure frontend CSS extraction using Lit `css` tagged template literals.
- **Small (S)**: Bounded to `services/rules_compendium/ui/src/`; all extracted files strictly < 150 lines.
- **Testable (T)**: Frontdoor verification through Storybook and blackbox UI component render tests.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Module Architecture**:
   - `runefoble-rules-compendium.styles.ts` reduced to strictly < 80 lines.
   - All extracted sub-stylesheets under `services/rules_compendium/ui/src/styles/` strictly < 150 lines.
2. **Frontdoor Test Verification**:
   - All tests pass via `uv run pytest tests/test_blackbox_rules_compendium_ui.py`.
3. **Quality Gates**:
   - Storybook stories render without errors.
   - Code passes `uv run ruff check .` and `uv run ruff format --check .`.
