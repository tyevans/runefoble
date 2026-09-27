---
id: '0234'
title: Campfire Crafting Styles Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0100
- TASK-0199
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0014
governing_stories:
- US-0044
target_release: 0.8.0
---

# TASK-0234: Campfire Crafting Styles Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/game_session/ui/src/runefoble-campfire-crafting.styles.ts` (307 lines, 61.4% of limit) into modular Lit CSS submodules under `services/game_session/ui/src/crafting/styles/` (`layout.styles.ts`, `recipes.styles.ts`, `mishaps.styles.ts`), ensuring all style modules remain strictly < 120 lines per Hard Invariant 6.

## Problem Statement
`services/game_session/ui/src/runefoble-campfire-crafting.styles.ts` bundles grid container styles, reagent slot styling, potion recipe list cards, volatile mishap animation keyframes, and rest boon badges into a single 307-line file. As new stronghold facility crafting stations are added, this file will breach the 500-line limit unless decomposed.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Modular CSS composition with Lit `css` tagged templates.
- **ADR-0012: Design System Theming and Bauhaus Modernism**: Bauhaus geometric tokens and high-contrast styling invariants.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Component subviews strictly < 150 lines.

## Scope of Work
1. **Layout Styles (`services/game_session/ui/src/crafting/styles/layout.styles.ts`)**:
   - Extract host container, tab navigation, and responsive grid layouts (< 100 lines).
2. **Recipe & Reagent Styles (`services/game_session/ui/src/crafting/styles/recipes.styles.ts`)**:
   - Extract reagent drop slots, potion cards, and crafting button states (< 100 lines).
3. **Mishap & Boon Styles (`services/game_session/ui/src/crafting/styles/mishaps.styles.ts`)**:
   - Extract volatile failure callouts, danger badges, and rest boon indicators (< 90 lines).
4. **Aggregator Export (`services/game_session/ui/src/runefoble-campfire-crafting.styles.ts`)**:
   - Compose the modular styles into `campfireCraftingStyles = [layoutStyles, recipeStyles, mishapStyles]` (< 40 lines).
5. **Verification**:
   - Verify Storybook stories for `<runefoble-campfire-crafting>` render without visual regression.

## Definition of Done
- `runefoble-campfire-crafting.styles.ts` reduced to < 40 lines.
- Extracted style submodules strictly < 120 lines each.
- Storybook stories render without errors.
- Passes `uv run pytest tests/test_blackbox_campfire_crafting.py`.
