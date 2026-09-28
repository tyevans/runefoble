---
id: '0327'
title: Spectator Overlay Styles Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0056
- TASK-0075
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds: []
governing_stories: []
target_release: 0.8.0
---

# TASK-0327: Spectator Overlay Styles Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/game_session/ui/src/runefoble-spectator-overlay.styles.ts` (271 lines, 54.2% of limit) into modular CSS sub-modules under `services/game_session/ui/src/styles/spectator/` (`spectator-base.styles.ts`, `spectator-vitals.styles.ts`, `spectator-narrative.styles.ts`), keeping each style file strictly < 100 lines per Hard Invariant 6.

## Problem Statement
`services/game_session/ui/src/runefoble-spectator-overlay.styles.ts` manages alpha-transparent stream layouts, party member vitals cards, status pill badges, active speaker waveforms, and narrative chronicle ticker styling in one file. As animated OBS lower-thirds and streaming layout presets expand, this file will approach the 500-line limit unless decomposed.

## Governing Architecture & ADRs
- **ADR-0004: Bauhaus Microfrontend Design System**: Design token inheritance and CSS custom properties.
- **ADR-0012: Theming System and Contrast Invariants**: Dark/Light mode theme compliance and WCAG contrast.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 100 lines).

## Scope of Work
1. **Base Stream & Layout Styles (`services/game_session/ui/src/styles/spectator/spectator-base.styles.ts`)**:
   - Host layout, transparent mode overrides, top/bottom/sidebar docking containers (< 80 lines).
2. **Party Vitals Card Styles (`services/game_session/ui/src/styles/spectator/spectator-vitals.styles.ts`)**:
   - Vitals cards, character avatar frames, HP progress bars, and status effect chips (< 85 lines).
3. **Narrative & Chronicle Ticker Styles (`services/game_session/ui/src/styles/spectator/spectator-narrative.styles.ts`)**:
   - Speaker pulse rings, dynamic lower-thirds, and chronicle log tickers (< 80 lines).
4. **Styles Aggregator (`services/game_session/ui/src/runefoble-spectator-overlay.styles.ts`)**:
   - Re-export composable array of CSSResult fragments (< 30 lines).
5. **Verification**:
   - Run frontend tests and Storybook build to ensure zero visual regressions.

## Definition of Done
- `runefoble-spectator-overlay.styles.ts` refactored into modular sub-modules.
- All extracted style submodules strictly < 100 lines each.
- Frontend test suite and Storybook components render with 100% pass rate.
