---
id: '0308'
title: Print Forge Component Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0105
governing_adrs:
- ADR-0004
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0015
governing_stories:
- US-0049
target_release: 0.8.0
---

# TASK-0308: Print Forge Component Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/asset_forge/ui/src/runefoble-print-forge.ts` (294 lines, 58.8% of limit) into modular subview templates under `services/asset_forge/ui/src/print_forge/` (`views/tiled-map-tab.ts`, `views/standees-tab.ts`, `views/stl-tokens-tab.ts`, `types.ts`), keeping each file strictly < 90 lines per Hard Invariant 6.

## Problem Statement
`services/asset_forge/ui/src/runefoble-print-forge.ts` consolidates three distinct physical tabletop export builders into one 294-line component:
1. Multi-page grid-calibrated battlemap PDF exporter with page size and overlap toggles.
2. Foldable papercraft standee generator with HP, names, and class icons.
3. Watertight 3D STL token ring generator with condition status clips.

As custom token frames, print preview canvases, and printer bleed calibration are added, this component will exceed 500 lines unless broken down into modular subviews.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Modular template decomposition and custom element styling.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation of tabletop export tools.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (subviews < 90 lines).

## Scope of Work
1. **Types Submodule (`services/asset_forge/ui/src/print_forge/types.ts`)**:
   - Extract `PrintForgeTab`, export event detail interfaces, and sizing types (< 40 lines).
2. **Tiled Map Tab View (`services/asset_forge/ui/src/print_forge/views/tiled-map-tab.ts`)**:
   - Extract grid dimensions, paper size selectors, and PDF export form (< 80 lines).
3. **Standees Tab View (`services/asset_forge/ui/src/print_forge/views/standees-tab.ts`)**:
   - Extract character standee configuration, HP bar toggles, and folding lines form (< 75 lines).
4. **STL Tokens Tab View (`services/asset_forge/ui/src/print_forge/views/stl-tokens-tab.ts`)**:
   - Extract 3D diameter inputs, status ring clip selectors, and mesh download controls (< 75 lines).
5. **Component Coordinator (`services/asset_forge/ui/src/runefoble-print-forge.ts`)**:
   - Coordinate event dispatching and render selected subview (< 90 lines).
6. **Verification**:
   - Run `npm test` and verify Storybook stories for print forge component.

## Definition of Done
- `runefoble-print-forge.ts` reduced to < 90 lines, delegating to `print_forge/views/` subviews.
- All extracted submodules strictly < 90 lines each per Hard Invariant 6.
- Storybook stories render and verify print forge options.
- All asset forge blackbox tests pass cleanly.
