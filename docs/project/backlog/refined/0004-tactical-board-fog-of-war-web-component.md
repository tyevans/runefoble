# TASK-0004: Tactical Board Fog-of-War and Token Web Component

## Description
Extend `frontend/src/components/runefoble-board.ts` with dynamic fog-of-war cell shading, token health indicators, and turn highlight overlays. Build corresponding Storybook stories in `frontend/src/stories/runefoble-board.stories.ts`.

## Governing Documents
- ADRs: ADR-0004
- PRDs: PRD-0001
- User Stories: US-0001, US-0004, US-0006

## Definition of Done
1. `<runefoble-board>` renders obscured fog-of-war cells outside player vision radii.
2. Active turn tokens display an animated golden glow.
3. Storybook contains interactive stories for `FogOfWarEncounter`, `ActiveTurn`, and `MultiplayerTokens`.
4. `pnpm run build-storybook` and `pnpm run build` pass with zero errors.
