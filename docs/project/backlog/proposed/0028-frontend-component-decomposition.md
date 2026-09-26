---
id: 0028
title: Frontend High-Complexity Component Decomposition & Storybook Sub-Modules
status: Proposed
created: 2026-09-25
dependencies: [TASK-0004, TASK-0012, TASK-0022]
governing_adrs: [ADR-0004, ADR-0012]
target_release: 0.2.0
---

# TASK-0028: Frontend High-Complexity Component Decomposition & Storybook Sub-Modules

## Status
Proposed

## Summary
Decompose oversized frontend Lit Web Components approaching Hard Invariant 6 (>400 lines) into focused, single-responsibility sub-components with isolated Shadow DOM encapsulation and dedicated Storybook stories.

## Problem Statement
The codebase health scan detected five frontend components nearing the 500-line hard invariant:
- `frontend/src/runefoble-app.ts` (452 lines)
- `frontend/src/components/runefoble-initiative-tracker.ts` (448 lines)
- `frontend/src/my-element.ts` (438 lines)
- `frontend/src/components/runefoble-absentee-recap.ts` (428 lines)
- `frontend/src/components/runefoble-spectator-view.ts` (417 lines)

These monolithic components mix view orchestration, canvas rendering, timer management, audio waveform visualization, and CSS theme definitions.

## Proposed Scope
1. **Initiative Tracker Decomposition**:
   - Extract `runefoble-turn-timer.ts` (Countdown ring, visual warnings, sound triggers).
   - Extract `runefoble-initiative-card.ts` (Individual character row, HP badge, condition pills).
2. **Absentee Recap Decomposition**:
   - Extract `runefoble-audio-player.ts` (Audio timeline scrubber, playback rate, waveform).
   - Extract `runefoble-chronicle-log.ts` (Story event entries, DM notes, penalty pills).
3. **App Shell Refactoring**:
   - Extract navigation header, modal dialogs, and session selector from `runefoble-app.ts`.
4. **Storybook Verification**:
   - Create isolated Storybook stories in `frontend/src/stories/` for all extracted sub-components.

## Acceptance Criteria
1. Every component file in `frontend/src/` strictly under 350 lines.
2. Zero regression in Storybook visual testing or `pnpm run build`.
3. Complete CSS styling encapsulation via Lit `css` tagged templates adhering to the Bauhaus theme.
