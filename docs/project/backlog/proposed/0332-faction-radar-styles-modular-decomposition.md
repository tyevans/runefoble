---
id: '0332'
title: Faction Radar Styles Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0126
- TASK-0137
- TASK-0195
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0017
governing_stories:
- US-0057
target_release: 0.8.0
---

# TASK-0332: Faction Radar Styles Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/the_watcher/ui/src/runefoble-faction-radar.styles.ts` (269 lines, 53.8% of limit) into modular sub-modules under `services/the_watcher/ui/src/styles/` (`faction-radar-layout.styles.ts`, `faction-radar-drawer.styles.ts`, and aggregator `runefoble-faction-radar.styles.ts`), keeping all style modules strictly < 110 lines per Hard Invariant 6.

## Problem Statement
`services/the_watcher/ui/src/runefoble-faction-radar.styles.ts` combines host container Bauhaus geometry, polar radar SVG styling, badge markers, side drawer panels, conflict feed cards, and responsive media queries in a single stylesheet. Future expansion of espionage alerts and turf war visual cues will push this stylesheet past the 500-line invariant unless decomposed.

## Governing Architecture & ADRs
- **ADR-0004: Bauhaus Microfrontend Design System**: Design token inheritance and CSS custom properties.
- **ADR-0012: Theming System and Contrast Invariants**: Dark/Light mode theme compliance and WCAG contrast.
- **ADR-0013: Modular Decomposition**: All style and component files kept strictly < 500 lines (submodules < 110 lines).

## Scope of Work
1. **Radar Layout & Canvas Styles (`services/the_watcher/ui/src/styles/faction-radar-layout.styles.ts`)**:
   - Extract host layout, header controls, badge styling, and polar SVG radar grid presentation (< 95 lines).
2. **Drawer & Intel Feed Styles (`services/the_watcher/ui/src/styles/faction-radar-drawer.styles.ts`)**:
   - Extract faction detail drawer, conflict feed rows, alert priority chips, and action buttons (< 100 lines).
3. **Aggregator Stylesheet (`services/the_watcher/ui/src/runefoble-faction-radar.styles.ts`)**:
   - Compose layout and drawer style modules into the exported `factionRadarStyles` array (< 30 lines).
4. **Verification**:
   - Verify component rendering and visual appearance in Storybook and frontend unit tests.

## Definition of Done
- `runefoble-faction-radar.styles.ts` decomposed into layout and drawer style modules.
- All extracted files strictly < 110 lines each per Hard Invariant 6.
- Frontend test runner and Storybook stories render the faction radar component with 100% pass rate.
