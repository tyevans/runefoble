---
id: '0043'
title: Frontend Microfrontend Component Styles and Subview Decomposition
status: Proposed
created: 2026-09-26
dependencies: [TASK-0011, TASK-0014, TASK-0022, TASK-0026]
governing_adrs: [ADR-0004, ADR-0012, ADR-0013]
target_release: 0.2.0
---

# TASK-0043: Frontend Microfrontend Component Styles and Subview Decomposition

## Status
Proposed

## Summary
Decompose monolithic Lit Web Component implementations in `@runefoble/game-session-ui` and `@runefoble/character-sheet-ui` that are approaching Hard Invariant 6 (File length limit < 500 lines). Extract large CSS style sheets into companion `.styles.ts` files and partition complex subviews into modular subcomponents.

## Problem Statement
Health scans identify three Lit Web Component files exceeding 400 lines (over 80% of the 500-line invariant):
- `services/game_session/ui/src/runefoble-initiative-tracker.ts` (448 lines)
- `services/character_sheet/ui/src/runefoble-absentee-recap.ts` (428 lines)
- `services/game_session/ui/src/runefoble-spectator-view.ts` (417 lines)

In all three components, inline `css` style declarations account for 120–180 lines, and complex interactive subviews (turn timers, combatant list rows, audio waveform canvases, chronicle event feeds) are bundled into the primary component definition file.

## Proposed Decomposition
1. **Initiative Tracker Decomposition (`services/game_session/ui/src/`)**:
   - Extract CSS declarations to `runefoble-initiative-tracker.styles.ts` (< 150 lines).
   - Component logic in `runefoble-initiative-tracker.ts` imports styles via `static styles = initiativeTrackerStyles;` (< 250 lines).
2. **Absentee Recap Decomposition (`services/character_sheet/ui/src/`)**:
   - Extract CSS declarations to `runefoble-absentee-recap.styles.ts` (< 140 lines).
   - Component logic in `runefoble-absentee-recap.ts` reduced to < 240 lines.
3. **Spectator View Decomposition (`services/game_session/ui/src/`)**:
   - Extract CSS declarations to `runefoble-spectator-view.styles.ts` (< 130 lines).
   - Component logic in `runefoble-spectator-view.ts` reduced to < 250 lines.

## Acceptance Criteria
1. Zero visual regression or breaking changes to CSS Custom Properties, Shadow DOM tokens, or public Lit element attributes.
2. All Storybook stories in `@runefoble/game-session-ui` and `@runefoble/character-sheet-ui` render identically with zero console errors.
3. All target files strictly under 300 lines (well below the 500-line limit).
4. `pnpm run build` and `uv run pytest tests/test_microfrontends.py` pass cleanly.
