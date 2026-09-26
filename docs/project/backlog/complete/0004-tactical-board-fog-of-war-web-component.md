# TASK-0004: Tactical Board Fog-of-War and Token Web Component

## Status
Complete

## Summary
Extended `<runefoble-board>` with dynamic fog-of-war cell shading, token health indicators, and turn highlight overlays. Added interactive Storybook stories showcasing fog-of-war exploration, active player turn indication with an animated golden glow, and multiplayer token arrays.

## Key Changes
- `frontend/src/components/runefoble-board.ts`:
  - Added `BoardToken` attributes: `hp`, `maxHp`, `visionRadius`, `isHostile`, `isActiveTurn`.
  - Added board properties: `fogOfWar: boolean`, `activeTurnTokenId: string`.
  - Implemented `isCellRevealed` spatial visibility calculation based on non-hostile token coordinates and vision radii.
  - Implemented dynamic fog shrouding (`.cell.fog`) with radial gradient vignettes obscuring hidden enemies and unmapped terrain.
  - Added animated golden glow (`@keyframes gold-pulse`) to highlight current active turn tokens.
  - Added token HP status bars with proportional color shifts (green > yellow > red).
  - Kept file concise and modular (362 lines, satisfying Hard Invariant 6).
- `frontend/src/stories/runefoble-board.stories.ts`:
  - Created interactive stories: `Default`, `ActiveEncounter`, `FogOfWarEncounter`, `ActiveTurn`, and `MultiplayerTokens`.
- Verified zero errors across `pnpm run build` and `pnpm run build-storybook`.

## Verification
- `pnpm --dir frontend run build`: Clean TypeScript check and Vite production bundle.
- `pnpm --dir frontend run build-storybook`: Clean Storybook build in 660ms with zero errors.
- `uv run pytest`: 59/59 tests pass.
- `helm lint deployments/helm/runefoble`: 0 charts failed.
