---
id: '0325'
title: Tavern Parlor Component Styles Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0103
- TASK-0307
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0014
governing_stories:
- US-0047
target_release: 0.8.0
---

# TASK-0325: Tavern Parlor Component Styles Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/game_session/ui/src/runefoble-tavern-parlor.styles.ts` (277 lines, 55.4% of limit) into modular CSS sub-modules under `services/game_session/ui/src/styles/tavern/` (`tavern-base.styles.ts`, `tavern-games.styles.ts`, `tavern-atmosphere.styles.ts`), keeping each style file strictly < 100 lines per Hard Invariant 6.

## Problem Statement
`services/game_session/ui/src/runefoble-tavern-parlor.styles.ts` defines layout styles, drinking contest audio visualizers, minigame selector buttons, Liar's dice cups, and atmosphere controls in a single monolithic file. As animated tavern encounters and DSP drinking slurs expand, this file will approach the 500-line invariant unless decomposed.

## Governing Architecture & ADRs
- **ADR-0004: Bauhaus Microfrontend Design System**: Design token inheritance and CSS custom properties.
- **ADR-0012: Theming System and Contrast Invariants**: Dark/Light mode theme compliance and WCAG contrast.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 100 lines).

## Scope of Work
1. **Base Parlor Styles (`services/game_session/ui/src/styles/tavern/tavern-base.styles.ts`)**:
   - Host layout, header controls, patron count badges, and action bar (< 80 lines).
2. **Minigame & Wager Styles (`services/game_session/ui/src/styles/tavern/tavern-games.styles.ts`)**:
   - Liar's Dice cup layout, bet controls, wagering chips, and victory banners (< 85 lines).
3. **Atmosphere & DSP Styles (`services/game_session/ui/src/styles/tavern/tavern-atmosphere.styles.ts`)**:
   - Drinking contest intoxication meter, slurred speech audio waveform, and ambient foley cues (< 80 lines).
4. **Styles Aggregator (`services/game_session/ui/src/runefoble-tavern-parlor.styles.ts`)**:
   - Re-export composable array of CSSResult fragments (< 30 lines).
5. **Verification**:
   - Run frontend tests and Storybook build to ensure zero visual regressions.

## Definition of Done
- `runefoble-tavern-parlor.styles.ts` refactored into modular sub-modules.
- All extracted style submodules strictly < 100 lines each.
- Frontend test suite and Storybook components render with 100% pass rate.
