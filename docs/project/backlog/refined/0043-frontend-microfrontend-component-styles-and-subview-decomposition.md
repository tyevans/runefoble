---
id: '0043'
title: Frontend Microfrontend Component Styles and Subview Decomposition
status: Refined
created: 2026-09-26
dependencies: [TASK-0011, TASK-0014, TASK-0022, TASK-0026]
governing_adrs: [ADR-0004, ADR-0012, ADR-0013]
target_release: 0.2.0
---

# TASK-0043: Frontend Microfrontend Component Styles and Subview Decomposition

## Status
Refined

## Summary
Decompose monolithic Lit Web Component implementations in `@runefoble/game-session-ui` and `@runefoble/character-sheet-ui` that are approaching Hard Invariant 6 (File length limit < 500 lines). Extract large CSS style sheets into companion `.styles.ts` files and partition complex subviews into modular subcomponents.

## Problem Statement
Health scans identify three Lit Web Component files exceeding 400 lines (over 80% of the 500-line invariant):
- `services/game_session/ui/src/runefoble-initiative-tracker.ts` (448 lines, 89.6% of limit)
- `services/character_sheet/ui/src/runefoble-absentee-recap.ts` (428 lines, 85.6% of limit)
- `services/game_session/ui/src/runefoble-spectator-view.ts` (417 lines, 83.4% of limit)

In all three components, inline `css` style declarations account for 120–180 lines, and complex interactive subviews (turn timers, combatant list rows, audio waveform canvases, chronicle event feeds) are bundled directly into the primary component definition file.

## INVEST Criteria Evaluation
- **Independent (I)**: Decomposes internal component styles and subviews without changing custom element tags (`<runefoble-initiative-tracker>`, `<runefoble-absentee-recap>`, `<runefoble-spectator-view>`), properties, or emitted CustomEvents.
- **Negotiable (N)**: Sub-module organization and `.styles.ts` file structures can be adapted per microfrontend package.
- **Valuable (V)**: Protects against Hard Invariant 6 violations across 3 prominent microfrontend UI packages; ensures style sheets are modular and reusable across Bauhaus themes.
- **Estimable (E)**: Standard Lit pattern of exporting `css` tagged templates to dedicated `*.styles.ts` modules.
- **Small (S)**: Scope confined strictly to extracting CSS style sheets and helper sub-renders across the three target microfrontends; all resulting files < 250 lines.
- **Testable (T)**: Verified via Storybook visual stories, TypeScript compiler checks (`tsc`), Vite bundle build (`pnpm run build`), and Python microfrontend tests (`tests/test_microfrontends.py`).

## Governing Architecture & ADRs
- **ADR-0004**: Lit Web Components and Storybook UI (Shadow DOM encapsulation and component architecture).
- **ADR-0012**: Design System Theming and Bauhaus Modernism (CSS Custom Properties, Bauhaus tokens, typography).
- **ADR-0013**: Microfrontend Architecture and Service Component Vendoring (bounded context ownership and manifest contracts).

## Proposed Decomposition
1. **Initiative Tracker Decomposition (`services/game_session/ui/src/`)**:
   - Extract CSS declarations to `runefoble-initiative-tracker.styles.ts` (< 150 lines).
   - Component logic in `runefoble-initiative-tracker.ts` imports styles via `static styles = [initiativeTrackerStyles];` (< 250 lines).
2. **Absentee Recap Decomposition (`services/character_sheet/ui/src/`)**:
   - Extract CSS declarations to `runefoble-absentee-recap.styles.ts` (< 140 lines).
   - Component logic in `runefoble-absentee-recap.ts` reduced to < 240 lines.
3. **Spectator View Decomposition (`services/game_session/ui/src/`)**:
   - Extract CSS declarations to `runefoble-spectator-view.styles.ts` (< 130 lines).
   - Component logic in `runefoble-spectator-view.ts` reduced to < 250 lines.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Style Extraction**:
   - Dedicated `*.styles.ts` companion modules created for all 3 components using Lit's `css` template tag.
2. **Contract Preservation**:
   - Zero changes to Custom Element tags, attributes, properties, or CustomEvents.
3. **File Length Compliance**:
   - All 6 target and extracted files strictly < 250 lines (well below the 500-line ceiling).
4. **Storybook & Frontdoor Blackbox Verification**:
   - All Storybook stories render cleanly with zero console warnings or errors.
   - `uv run pytest tests/test_microfrontends.py` passes 100% via public HTTP manifest endpoints (`/ui/manifest`).
5. **Build & Quality Gate Verification**:
   - `pnpm run build` succeeds cleanly across all UI packages and the frontend App Shell.
