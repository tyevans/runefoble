---
id: '0111'
title: Settings Modal Styles and Sub-Component CSS Modular Decomposition
status: Complete
created: 2026-09-26
dependencies:
- TASK-0073
- TASK-0086
governing_adrs:
- ADR-0004
- ADR-0009
- ADR-0012
- ADR-0013
target_release: 0.3.0
governing_prds:
- PRD-0004
- PRD-0012
governing_stories:
- US-0012
pr_url: https://github.com/tyevans/runefoble/pull/117
---
# TASK-0111: Settings Modal Styles and Sub-Component CSS Modular Decomposition

## Status
Refined

## Summary
Decompose `frontend/src/components/runefoble-settings-modal.styles.ts` (356 lines, 71.2% of limit) into modular CSS sub-modules (`settings-modal-dialog.styles.ts`, `settings-modal-tabs.styles.ts`, `settings-modal-controls.styles.ts`) to prevent breaching Hard Invariant 6 (File length limit < 500 lines) as new streaming, broadcast overlay, and accessibility settings tabs are introduced.

## Problem Statement
`frontend/src/components/runefoble-settings-modal.styles.ts` currently aggregates all CSS styling rules for the settings system into a single 356-line template:
1. Modal overlay, backdrop blur filters, and dialog window layout animations (`rf-fade-in`, `rf-slide-up`).
2. Tab bar navigation buttons, active state indicators, and mobile responsive overflow.
3. Form controls, radio option cards, appearance mode toggles (dark/light/system), theme preview swatches, and high-contrast accessibility sliders.
4. Action footer, save/close buttons, and keybinding cheat sheet tables.

As Milestone 4 introduces spectator broadcast overlay settings (TASK-0056) and campaign telemetry preference controls (TASK-0110), this style module will grow beyond 500 lines unless partitioned into modular CSS partials.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Strict Shadow DOM encapsulation and Bauhaus geometric design tokens.
- **ADR-0009: Frontend State and Design System Architecture**: Modular styles and CSS custom properties.
- **ADR-0012: CSS Custom Properties and Dark/Light Mode Theming**: Color mode token encapsulation and contrast ratios.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Component boundary isolation.

## Product & User Story References
- **Product Requirements**:
  - [`prd-0004-dynamic-vocal-audio-conditioning-and-dsp-filters.md`](../../product/accepted/prd-0004-dynamic-vocal-audio-conditioning-and-dsp-filters.md)
  - [`prd-0012-campaign-telemetry-and-living-chronicle-timeline.md`](../../product/accepted/prd-0012-campaign-telemetry-and-living-chronicle-timeline.md)
- **User Story**:
  - [`us-0012-spatial-line-of-sight-and-fog-of-war.md`](../../user_stories/accepted/us-0012-spatial-line-of-sight-and-fog-of-war.md)

## Proposed Decomposition
1. **Modal Layout & Overlay Styles (`frontend/src/components/styles/settings-modal-layout.styles.ts`)**:
   - Overlay backdrop, dialog container, header, footer action buttons, and responsive breakpoints (< 130 lines).
2. **Tabs & Option Cards Styles (`frontend/src/components/styles/settings-modal-tabs.styles.ts`)**:
   - Tab navigation bars, tab panel transitions, radio toggle cards, and setting group descriptions (< 130 lines).
3. **Appearance & Controls Styles (`frontend/src/components/styles/settings-modal-controls.styles.ts`)**:
   - Color swatch previews, select inputs, slider tracks, and typography previews (< 120 lines).
4. **Composite Export (`frontend/src/components/runefoble-settings-modal.styles.ts`)**:
   - Clean array composition: `export const settingsModalStyles = [layoutStyles, tabsStyles, controlsStyles];` (< 30 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Modularizes internal CSS style arrays without changing the `<runefoble-settings-modal>` component API or DOM markup.
- **Negotiable (N)**: Split boundaries between layout and control styling can be tailored.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (< 500 lines) and enables reuse of styled form controls across other modals.
- **Estimable (E)**: Pure Lit `css` tagged template literal decomposition.
- **Small (S)**: Scope strictly isolated to `frontend/src/components/runefoble-settings-modal.styles.ts`; all resulting files < 140 lines.
- **Testable (T)**: Verified with `pnpm run build` and Storybook visual tests via `tests/test_theming.py`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Style Decomposition**:
   - `runefoble-settings-modal.styles.ts` decomposed into focused style modules strictly under 150 lines each.
2. **Visual Invariant Preservation**:
   - 100% visual consistency preserved across all settings tabs in Storybook with zero console errors.
3. **Strict Line Limit Enforced**:
   - Every file strictly under 150 lines in compliance with Hard Invariant 6.
4. **Quality Gates**:
   - Passes `pnpm run build` with zero TypeScript or Lit compilation errors and `uv run pytest tests/test_theming.py`.
