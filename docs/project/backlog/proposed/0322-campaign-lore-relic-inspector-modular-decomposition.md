---
id: '0322'
title: Campaign Lore Relic Inspector Component Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0101
- TASK-0297
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0015
governing_stories:
- US-0045
target_release: 0.8.0
---

# TASK-0322: Campaign Lore Relic Inspector Component Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/campaign_lore/ui/src/runefoble-relic-inspector.ts` (285 lines, 57.0% of limit) into modular sub-modules under `services/campaign_lore/ui/src/` (`styles/relic-inspector.styles.ts`, `controllers/relic-viewport-controller.ts`, and core component `runefoble-relic-inspector.ts`), keeping all source files strictly < 120 lines per Hard Invariant 6.

## Problem Statement
`services/campaign_lore/ui/src/runefoble-relic-inspector.ts` encapsulates Bauhaus styling, WebGL/2D canvas rendering and rotation math, rune hotspot collision detection, and HTML UI template rendering into a single monolithic file. As interactive 3D lighting, particle effects, and audio acoustic cues are added, this component will exceed the 500-line invariant unless decomposed.

## Governing Architecture & ADRs
- **ADR-0004: Bauhaus Microfrontend Design System**: Design token inheritance and CSS custom properties.
- **ADR-0012: Theming System and Contrast Invariants**: Dark/Light mode theme compliance and WCAG contrast.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 120 lines).

## Scope of Work
1. **Relic Inspector Styles (`services/campaign_lore/ui/src/styles/relic-inspector.styles.ts`)**:
   - Extract host layout, viewport, canvas framing, overlay HUD, and control buttons into modular CSS (< 90 lines).
2. **Viewport & Raycasting Controller (`services/campaign_lore/ui/src/controllers/relic-viewport-controller.ts`)**:
   - Extract rotation angle state, drag gesture listeners, 3D projection, and rune hitbox hover checks (< 100 lines).
3. **Core Component Refactoring (`services/campaign_lore/ui/src/runefoble-relic-inspector.ts`)**:
   - Wire styles and controller into the Lit element, keeping presentation templates clean (< 110 lines).
4. **Verification**:
   - Run frontend tests and Storybook build to ensure zero visual regressions.

## Definition of Done
- `runefoble-relic-inspector.ts` decomposed into styles and controller sub-modules.
- All extracted files strictly < 120 lines each per Hard Invariant 6.
- Frontend test suite and Storybook components render with 100% pass rate.
