---
id: 0195
title: Faction Radar SVG and Drawer Subviews Modular Decomposition
status: Complete
created: 2026-09-27
dependencies:
- TASK-0126
- TASK-0137
governing_adrs:
- ADR-0004
- ADR-0007
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0017
governing_stories:
- US-0057
target_release: 0.7.0
pr_url: https://github.com/tyevans/runefoble/pull/256
---
# TASK-0195: Faction Radar SVG and Drawer Subviews Modular Decomposition

## Status
Refined

## Summary
Decompose `services/the_watcher/ui/src/runefoble-faction-radar.ts` (331 lines, 66.2% of limit) into modular subviews under `services/the_watcher/ui/src/faction_radar/` (`radar-svg.template.ts`, `bulletin-drawer.template.ts`, and `faction-details.template.ts`), keeping each subview strictly < 120 lines per Hard Invariant 6 and ADR-0004/ADR-0013.

## Problem Statement
`services/the_watcher/ui/src/runefoble-faction-radar.ts` contains 331 lines combining SVG geometric math (polar-to-cartesian projection, multi-axis radar polygons, data vertices), sliding bulletin drawers, tavern rumor tickers, and faction inspection cards. With upcoming espionage feeds and bribery dials in Milestone 9, this component will exceed 400 lines unless broken down into modular template components.

## Governing Architecture & ADRs
- **ADR-0004: Frontend Visualizer & Lit Component Architecture**: Separation of SVG math and layout templates from Lit custom element controllers.
- **ADR-0007: Domain-Driven Design Architecture**: Keeping faction intelligence presentation isolated in The Watcher bounded context.
- **ADR-0012: Theming Tokens & Bauhaus Design System**: Adherence to high-contrast geometric tokens and color modes.
- **ADR-0013: Microfrontend Bounded Context Architecture**: UI encapsulation within `services/the_watcher/ui/`.

## Detailed Specification & Implementation Plan
1. **Modular Subview Templates (`services/the_watcher/ui/src/faction_radar/`)**:
   - `radar-svg.template.ts`: Mathematical calculations and SVG elements for polar grid circles, radial axes, faction polygons, and vertex hit targets (< 110 lines).
   - `bulletin-drawer.template.ts`: Intelligence bulletin drawer, world tick history, tavern rumors accordion, and regional unrest feeds (< 100 lines).
   - `faction-details.template.ts`: Selected faction inspection card, influence progress bar, resource indicators, and rival faction tags (< 90 lines).
2. **Component Controller Refactoring (`services/the_watcher/ui/src/runefoble-faction-radar.ts`)**:
   - Reduce core component to state management, drawer toggling, event dispatching, and importing modular templates (< 110 lines).
3. **Verification**:
   - Verify Storybook stories for `<runefoble-faction-radar>` render correctly and drawer interactions operate smoothly.
   - Run existing blackbox tests for faction intelligence to verify zero regressions.

## INVEST Criteria Evaluation
- **Independent (I)**: Isolated entirely within `services/the_watcher/ui/src/` microfrontend.
- **Negotiable (N)**: Logical partition divides SVG polygon math, drawer UI, and faction detail cards.
- **Valuable (V)**: Protects against Hard Invariant 6 and clarifies radar geometry vs drawer logic.
- **Estimable (E)**: Discrete template extractions with well-defined inputs and event callbacks.
- **Small (S)**: Scope strictly isolated to `<runefoble-faction-radar>` templates (< 120 lines each).
- **Testable (T)**: Frontdoor validation via Storybook stories and existing blackbox tests.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Module Architecture**:
   - `runefoble-faction-radar.ts` reduced to strictly < 120 lines.
   - Sub-modules in `services/the_watcher/ui/src/faction_radar/` strictly < 120 lines each.
2. **Frontdoor Verification**:
   - Storybook stories render without errors or styling regressions.
   - Relevant blackbox test suites pass via `uv run pytest tests/test_blackbox_faction_radar.py` or equivalent watcher UI tests.
3. **Quality Gates**:
   - Code passes `uv run ruff check .` and `uv run ruff format --check .`.
   - Microfrontend bundle builds cleanly via `pnpm run build`.
