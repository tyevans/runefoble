---
id: '0061'
title: Tactical Board, Autonomous DM, and Voice Controls Microfrontend Styles Decomposition
status: Proposed
created: 2026-09-26
dependencies: [TASK-0004, TASK-0013, TASK-0027]
governing_adrs: [ADR-0004, ADR-0012, ADR-0013]
target_release: 0.2.0
---

# TASK-0061: Tactical Board, Autonomous DM, and Voice Controls Microfrontend Styles Decomposition

## Status
Proposed

## Summary
Decompose monolithic Lit Web Component implementations in `@runefoble/board-state-ui`, `@runefoble/the-watcher-ui`, and `@runefoble/voice-agent-ui` that are approaching Hard Invariant 6 (File length limit < 500 lines). Extract large CSS stylesheets into companion `.styles.ts` files, bringing all component logic and stylesheet files well below 250 lines.

## Problem Statement
Health scans and file size audits identify the remaining three primary microfrontend component implementations approaching the 400-line threshold:
- `services/board_state/ui/src/runefoble-board.ts` (385 lines, 77.0% of limit; 217 lines of CSS)
- `services/the_watcher/ui/src/runefoble-autonomous-dm.ts` (382 lines, 76.4% of limit; 221 lines of CSS)
- `services/voice_agent/ui/src/runefoble-voice-controls.ts` (379 lines, 75.8% of limit; 150 lines of CSS)

In each of these components, CSS styles comprise over 40%–58% of total file length. When combined with interactive rendering loops, WebSocket message dispatchers, and state properties, any upcoming feature addition risks breaching the 500-line hard invariant ceiling.

## Proposed Decomposition
1. **Board State Microfrontend (`services/board_state/ui/src/`)**:
   - Extract CSS declarations to `runefoble-board.styles.ts` (< 220 lines).
   - Retain component lifecycle, canvas rendering, token positioning, and shroud masking in `runefoble-board.ts` (< 190 lines).
2. **The Watcher Microfrontend (`services/the_watcher/ui/src/`)**:
   - Extract CSS declarations to `runefoble-autonomous-dm.styles.ts` (< 230 lines).
   - Retain scene atmosphere displays, tactical prompt controls, and DM override buttons in `runefoble-autonomous-dm.ts` (< 190 lines).
3. **Voice Agent Microfrontend (`services/voice_agent/ui/src/`)**:
   - Extract CSS declarations to `runefoble-voice-controls.styles.ts` (< 160 lines).
   - Retain WebRTC connection triggers, room status indicators, and DSP filter sliders in `runefoble-voice-controls.ts` (< 240 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Decomposes internal component styles without changing custom element tags (`<runefoble-board>`, `<runefoble-autonomous-dm>`, `<runefoble-voice-controls>`), properties, or emitted CustomEvents.
- **Negotiable (N)**: CSS file naming and token import structure can be adapted per package.
- **Valuable (V)**: Protects against Hard Invariant 6 violations across all remaining service UI packages and enhances stylesheet reusability across Bauhaus themes.
- **Estimable (E)**: Standard Lit pattern of exporting `css` tagged templates to dedicated `*.styles.ts` modules, identical to TASK-0043.
- **Small (S)**: Scope strictly isolated to stylesheet extraction across the three target microfrontends; all resulting files < 250 lines.
- **Testable (T)**: Verified via Storybook visual stories, TypeScript compiler checks (`pnpm run build`), and Python microfrontend tests (`tests/test_microfrontends.py`).

## Acceptance Criteria
1. Dedicated `*.styles.ts` companion modules created for all 3 components using Lit's `css` template tag.
2. All modified and new files strictly under 250 lines.
3. Zero breaking changes to custom element tags, properties, or CustomEvents.
4. Clean build pass on `pnpm run build` and 100% pass on `uv run pytest tests/test_microfrontends.py`.
5. Storybook stories render without visual degradation or console errors.
