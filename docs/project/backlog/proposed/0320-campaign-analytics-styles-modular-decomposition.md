---
id: '0320'
title: Campaign Analytics Component Styles Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0052
- TASK-0110
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds: []
governing_stories: []
target_release: 0.8.0
---

# TASK-0320: Campaign Analytics Component Styles Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/campaign_analytics/ui/src/runefoble-campaign-analytics.styles.ts` (286 lines, 57.2% of limit) into modular CSS sub-modules under `services/campaign_analytics/ui/src/styles/` (`analytics-base.styles.ts`, `analytics-charts.styles.ts`, `analytics-timeline.styles.ts`), keeping each style file strictly < 100 lines per Hard Invariant 6.

## Problem Statement
`services/campaign_analytics/ui/src/runefoble-campaign-analytics.styles.ts` defines layout styles, telemetry stat cards, spatial damage heatmap canvas styling, chronicle timeline entries, and MVP award badges. As telemetry tracking and encounter charts expand, this monolithic style file will approach the 500-line limit unless decomposed into clean, modular CSS fragments.

## Governing Architecture & ADRs
- **ADR-0004: Bauhaus Microfrontend Design System**: Design token inheritance and CSS custom properties.
- **ADR-0012: Theming System and Contrast Invariants**: Dark/Light mode theme compliance and WCAG contrast.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 100 lines).

## Scope of Work
1. **Base Analytics Styles (`services/campaign_analytics/ui/src/styles/analytics-base.styles.ts`)**:
   - Host layout, header controls, metric summary cards, and MVP highlight badges (< 80 lines).
2. **Chart & Heatmap Styles (`services/campaign_analytics/ui/src/styles/analytics-charts.styles.ts`)**:
   - Spatial damage heatmap canvas, turn-duration bar graphs, and telemetry tooltips (< 80 lines).
3. **Timeline & Archive Styles (`services/campaign_analytics/ui/src/styles/analytics-timeline.styles.ts`)**:
   - Chronicle event timeline list, narrative filters, and session milestone cards (< 80 lines).
4. **Styles Aggregator (`services/campaign_analytics/ui/src/runefoble-campaign-analytics.styles.ts`)**:
   - Re-export composable array of CSSResult fragments (< 30 lines).
5. **Verification**:
   - Run frontend tests and Storybook build to ensure zero visual regressions.

## Definition of Done
- `runefoble-campaign-analytics.styles.ts` refactored into modular sub-modules.
- All extracted style submodules strictly < 100 lines each.
- Frontend test suite and Storybook components render with 100% pass rate.
