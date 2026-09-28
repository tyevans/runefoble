---
id: '0323'
title: Campaign Lore Handout Viewer Component Modular Decomposition
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

# TASK-0323: Campaign Lore Handout Viewer Component Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/campaign_lore/ui/src/runefoble-handout-viewer.ts` (283 lines, 56.6% of limit) into modular sub-modules under `services/campaign_lore/ui/src/` (`styles/handout-viewer.styles.ts`, `controllers/handout-seal-controller.ts`, and core component `runefoble-handout-viewer.ts`), keeping all source files strictly < 120 lines per Hard Invariant 6.

## Problem Statement
`services/campaign_lore/ui/src/runefoble-handout-viewer.ts` contains inline styles for antique parchment texture and wax seal physics, seal-breaking event handlers, UV invisible ink lamp toggles, and Lit HTML template rendering. As diegetic sensory effects and acoustic feedback cues expand, this file will threaten the 500-line limit unless decomposed into focused modules.

## Governing Architecture & ADRs
- **ADR-0004: Bauhaus Microfrontend Design System**: Design token inheritance and CSS custom properties.
- **ADR-0012: Theming System and Contrast Invariants**: Dark/Light mode theme compliance and WCAG contrast.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 120 lines).

## Scope of Work
1. **Handout Viewer Styles (`services/campaign_lore/ui/src/styles/handout-viewer.styles.ts`)**:
   - Extract host layout, antique parchment framing, wax seal stamps, UV ink glow animations, and badges (< 90 lines).
2. **Seal & UV Controller (`services/campaign_lore/ui/src/controllers/handout-seal-controller.ts`)**:
   - Extract wax seal break state transitions, acoustic cue dispatch, and UV lamp reveal logic (< 90 lines).
3. **Core Component Refactoring (`services/campaign_lore/ui/src/runefoble-handout-viewer.ts`)**:
   - Refactor Lit component to import extracted styles and delegate state interactions to the controller (< 110 lines).
4. **Verification**:
   - Run frontend tests and Storybook build to ensure zero visual regressions.

## Definition of Done
- `runefoble-handout-viewer.ts` decomposed into styles and controller sub-modules.
- All extracted files strictly < 120 lines each per Hard Invariant 6.
- Frontend test suite and Storybook components render with 100% pass rate.
