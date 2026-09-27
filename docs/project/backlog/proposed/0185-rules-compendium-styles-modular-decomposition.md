---
id: '0185'
title: Rules Compendium Styles Modular Decomposition
status: Proposed
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
Proposed

## Summary
Decompose `services/rules_compendium/ui/src/runefoble-rules-compendium.styles.ts` (357 lines, 71.4% of limit) by extracting encounter builder styles, homebrew form styles, and search filter styles into modular sub-stylesheets, keeping all style modules strictly < 150 lines per Hard Invariant 6.

## Problem Statement
`services/rules_compendium/ui/src/runefoble-rules-compendium.styles.ts` contains all CSS Lit tagged template literals for the compendium search view, filter tabs, monster stat blocks, homebrew creation forms, and CR encounter calculator. At 357 lines, it approaches the 400-line threshold and should be decomposed into focused CSS modules.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean modular package structure.
- **ADR-0012: Bauhaus Geometric Design System**: Tokenized CSS custom properties and theme contrast invariants.
- **ADR-0013: Microfrontend Architecture and Bounded Context UI**: Encapsulated component styles within service UI packages.

## Scope of Work
1. **Base & Layout Styles (`services/rules_compendium/ui/src/styles/compendium-base.styles.ts`)**:
   - Extract search bar, filter tabs, navigation pills, and header layout (< 100 lines).
2. **Encounter Builder Styles (`services/rules_compendium/ui/src/styles/encounter-builder.styles.ts`)**:
   - Extract encounter difficulty meter, monster badge tags, and party CR thresholds (< 120 lines).
3. **Homebrew Form Styles (`services/rules_compendium/ui/src/styles/homebrew-form.styles.ts`)**:
   - Extract form inputs, stat block preview grids, and action button groups (< 110 lines).
4. **Aggregator (`services/rules_compendium/ui/src/runefoble-rules-compendium.styles.ts`)**:
   - Aggregate sub-stylesheets into exported `compendiumStyles` array (< 60 lines).
5. **Verification**:
   - Verify Storybook stories and component renders with `npm run test` or Storybook build.

## Definition of Done
- `runefoble-rules-compendium.styles.ts` reduced to < 80 lines.
- All extracted sub-stylesheets strictly < 150 lines.
- Microfrontend passes build and rendering checks.
- Code passes formatting and linting checks.
