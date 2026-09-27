---
id: '0159'
title: DM Hidden Layers & Multi-Map Switcher Microfrontend
status: Proposed
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
Proposed

## Summary
Build `<runefoble-dm-trap-controls>` and `<runefoble-map-switcher>` Web Components in `services/board_state/ui/src/` to provide DM-exclusive controls for placing hidden traps, configuring trigger radiuses, and executing mid-session battlemap switches.

## Problem Statement
Game Masters managing dynamic dungeons need straightforward tactile controls on the board to drag-and-drop trap markers, preview trigger danger zones (visible only to DM), and execute seamless map switches without reloading the browser.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Modular Lit Web Components.
- **ADR-0012: Theming System and Accessibility Contrast Invariants**: Distinct danger zone highlights and theme styling.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Vendored in `services/board_state/ui/`.

## Scope of Work
1. **DM Hidden Layer Toolbar**:
   - Palette for selecting trap types (spike pit, glyph of warding, tripwire) and arming cells (< 140 lines).
2. **Multi-Map Switcher Modal**:
   - Quick-switcher thumbnail grid of active campaign battlemaps with one-click teleport action (< 140 lines).
3. **Storybook Stories**:
   - Stories showcasing DM layer toggling, trap arming, and map transition previews.
4. **Manifest Export**:
   - Export custom elements via `services/board_state/` UI manifest.
