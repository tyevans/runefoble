---
id: '0318'
title: Campaign Atlas Styles Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0106
- TASK-0185
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds: []
governing_stories: []
target_release: 0.8.0
---

# TASK-0318: Campaign Atlas Styles Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/campaign_lore/ui/src/runefoble-campaign-atlas.styles.ts` (287 lines, 57.4% of limit) into modular CSS sub-modules under `services/campaign_lore/ui/src/styles/` (`atlas-base.styles.ts`, `atlas-layers.styles.ts`, `atlas-pins.styles.ts`, `atlas-details.styles.ts`), keeping each style file strictly < 100 lines per Hard Invariant 6.

## Problem Statement
`services/campaign_lore/ui/src/runefoble-campaign-atlas.styles.ts` encapsulates the visual layout, layer control drawers, milestone pin markers, filter panels, and detail modals for the interactive campaign world atlas. As additional geospatial layers, terrain overlays, and settlement havens are rendered on the map, this monolithic styles file will approach the 500-line limit unless decomposed into specialized style modules.

## Governing Architecture & ADRs
- **ADR-0004: Bauhaus Microfrontend Design System**: Design token inheritance and CSS custom properties.
- **ADR-0012: Theming System and Contrast Invariants**: Dark/Light mode theme compliance and WCAG contrast.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 100 lines).

## Scope of Work
1. **Base Atlas Styles (`services/campaign_lore/ui/src/styles/atlas-base.styles.ts`)**:
   - Host container, top bar, title group, zoom controls, and canvas container styles (< 80 lines).
2. **Layer Drawer Styles (`services/campaign_lore/ui/src/styles/atlas-layers.styles.ts`)**:
   - Layer toggles, opacity sliders, visibility indicators, and legend panels (< 80 lines).
3. **Pin Marker & Filter Styles (`services/campaign_lore/ui/src/styles/atlas-pins.styles.ts`)**:
   - Milestone pin badges, era filters, coordinate overlays, and icon glyphs (< 80 lines).
4. **Detail Drawer & Dialog Styles (`services/campaign_lore/ui/src/styles/atlas-details.styles.ts`)**:
   - Location preview drawers, parchment lore inspection dialogs, and action buttons (< 80 lines).
5. **Styles Aggregator (`services/campaign_lore/ui/src/runefoble-campaign-atlas.styles.ts`)**:
   - Re-export composable array of CSSResult fragments (< 30 lines).
6. **Verification**:
   - Run frontend tests and Storybook build to ensure zero visual regressions.

## Definition of Done
- `runefoble-campaign-atlas.styles.ts` refactored to aggregate sub-modules.
- All extracted style submodules strictly < 100 lines each.
- Frontend test suite and Storybook components render with 100% pass rate.
