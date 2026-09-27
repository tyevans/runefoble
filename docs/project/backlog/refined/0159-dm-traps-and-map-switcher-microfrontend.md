---
id: '0159'
title: DM Hidden Layers & Multi-Map Switcher Microfrontend
status: Refined
created: 2026-09-26
dependencies:
- TASK-0156
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0007
governing_stories:
- US-0018
target_release: 0.6.0
---

# TASK-0159: DM Hidden Layers & Multi-Map Switcher Microfrontend

## Status
Refined

## Summary
Build `<runefoble-dm-trap-controls>` and `<runefoble-map-switcher>` Web Components in `services/board_state/ui/src/` to provide DM-exclusive controls for placing hidden traps, configuring trigger radiuses, and executing mid-session battlemap switches.

## Problem Statement
Game Masters managing dynamic dungeons need straightforward tactile controls on the board to drag-and-drop trap markers, preview trigger danger zones (visible only to DM), and execute seamless map switches without reloading the browser.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Encapsulated Lit Web Components with Shadow DOM.
- **ADR-0012: Theming System and Accessibility Contrast Invariants**: Distinct danger zone highlights and theme styling.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Vendored strictly in `services/board_state/ui/`.

## Product & User Story References
- **Product Requirement**: [`prd-0007-tactile-virtual-tabletop-board.md`](../../product/accepted/prd-0007-tactile-virtual-tabletop-board.md)
- **User Story**: [`us-0018-dm-spatial-traps-and-map-triggers.md`](../../user_stories/accepted/us-0018-dm-spatial-traps-and-map-triggers.md)

## Detailed Specification & Implementation Plan
1. **DM Hidden Layer Toolbar (`services/board_state/ui/src/runefoble-dm-trap-controls.ts`)**:
   - Palette for selecting trap types (spike pit, glyph of warding, tripwire) and arming cells (< 140 lines).
2. **Multi-Map Switcher Modal (`services/board_state/ui/src/runefoble-map-switcher.ts`)**:
   - Quick-switcher thumbnail grid of active campaign battlemaps with one-click teleport action (< 140 lines).
3. **Component Styles (`services/board_state/ui/src/runefoble-dm-trap-controls.styles.ts`)**:
   - Bauhaus-aligned styles and DM-only HUD styling (< 110 lines).
4. **Storybook Stories (`services/board_state/ui/src/runefoble-dm-trap-controls.stories.ts`)**:
   - Stories showcasing DM layer toggling, trap arming, and map transition previews (< 130 lines).
5. **Manifest Export & Integration**:
   - Export custom elements via `services/board_state/` UI manifest and verify `/ui/manifest`.

## INVEST Criteria Evaluation
- **Independent (I)**: Consumes existing trap management endpoints from TASK-0156 without changing underlying board mechanics.
- **Negotiable (N)**: Trap icons and palette styling can be adjusted.
- **Valuable (V)**: Streamlines DM encounter staging and prevents accidental player reveals.
- **Estimable (E)**: Standard Lit components with modal state and drag-and-drop handles.
- **Small (S)**: Bounded strictly to `services/board_state/ui/src/`; all files < 160 lines.
- **Testable (T)**: Storybook stories verify visual rendering and blackbox tests verify `/ui/manifest`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Microfrontend Architecture**:
   - Built and vendored inside `services/board_state/ui/`.
   - All TypeScript and CSS files strictly < 160 lines per Hard Invariant 6.
2. **Storybook Verification**:
   - Interactive stories render cleanly in Storybook with zero console errors.
3. **Frontdoor Test Verification**:
   - Blackbox test suite `tests/test_blackbox_dm_traps_ui/` asserts `/ui/manifest` export and custom element script bundles.
4. **Quality Gates**:
   - Passes `pnpm run build`, `uv run ruff check .`, and `uv run ruff format --check .`.
