---
id: '0487'
title: Tactile Board GM God-Mode Workspace and Fog-of-War Paintbrush
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0004
- TASK-0007
- TASK-0156
- TASK-0159
governing_adrs:
- ADR-0001
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0003
- PRD-0013
governing_stories:
- US-0013
- US-0043
target_release: 0.9.0
---

# TASK-0487: Tactile Board GM God-Mode Workspace and Fog-of-War Paintbrush

## Status
Proposed

## Summary
Implement a GM God-Mode tactical workspace drawer (`services/board_state/ui/src/runefoble-gm-workspace.ts`) for `<runefoble-board>` providing Game Masters with an omniscient viewport layer, manual fog-of-war reveal/shroud paintbrush tools with adjustable brush radius, secret encounter annotation pins, and a quick monster/NPC spawner palette that places new tokens onto the tactical grid with fine-grained Zanzibar authorization guards per PRD-0013.

## Problem Statement
Game Masters currently have limited direct in-canvas tools to manipulate tactical environments on the fly. Revealing a hidden alcove or shrouded secret chamber requires manually moving player tokens or disabling global fog. Additionally, spawning reinforcements requires switching away from the board to separate compendium or session screens. PRD-0013 requires a unified GM God-Mode workspace with a manual fog paintbrush, hidden GM-only pins, and a quick token spawner drawer accessible directly from the board canvas without disrupting player viewports.

## Governing Architecture & ADRs
- **ADR-0001: Google Zanzibar for Fine-Grained Authorization**: Ensure GM God-Mode controls are strictly rendered for users with `run_session` or `manage` permissions on the active campaign.
- **ADR-0004: Lit Web Components and Storybook UI**: Modular drawer component adhering to Bauhaus layout tokens and Shadow DOM encapsulation.
- **ADR-0012: CSS Custom Properties & Bauhaus Design Tokens**: Floating tool palette with consistent iconography, active tool indicators, and responsive drawer animations.
- **ADR-0013: Frontend Microfrontend Architecture**: Dispatches standardized board mutation events (`@shroud-brush-applied`, `@token-spawn-requested`, `@gm-note-placed`).

## Product & User Story References
- [`prd-0003-spatial-fog-of-war-and-visibility-engine.md`](../../product/accepted/prd-0003-spatial-fog-of-war-and-visibility-engine.md)
- [`prd-0013-immersive-and-intuitive-frontend-experience.md`](../../product/accepted/prd-0013-immersive-and-intuitive-frontend-experience.md)
- [`us-0043-tactile-kinetic-board-and-spoken-ghost-previews.md`](../../user_stories/accepted/us-0043-tactile-kinetic-board-and-spoken-ghost-previews.md)

## Scope of Work
1. **GM God-Mode Tool Palette (`services/board_state/ui/src/runefoble-gm-workspace.ts`)**:
   - Floating collapsible toolbar for authenticated GMs (`isGm=true`).
   - Tools:
     - `Paintbrush (Reveal)`: Dragging across the board reveals fog-of-war shroud cells within circular brush radius (1, 2, or 3 cells).
     - `Paintbrush (Shroud)`: Dragging across the board re-cloaks revealed cells back into darkness.
     - `Secret Note Pin`: Drop hidden GM-only narrative notes onto grid coordinates.
     - `Monster Spawner Palette`: Quick-search dropdown of monster templates (Goblin, Skeleton, Orc, Wolf) with drag-and-drop placement onto grid cells.
2. **Fog Shroud Paintbrush Canvas Integration (`services/board_state/ui/src/runefoble-board.ts`)**:
   - Listen for pointer drag events when GM paintbrush mode is active.
   - Dispatch `@shroud-cells-updated` with modified coordinate sets, emitting `runefoble.events.board.shroud_updated` domain event.
3. **Storybook Stories**:
   - Author Storybook stories demonstrating GM God-Mode tool selection, paintbrush stroke application, and monster placement.

## Definition of Done
1. `runefoble-gm-workspace.ts` implemented and mounts within board container when user possesses GM permissions.
2. Fog reveal and shroud paintbrush updates grid shroud array with real-time visual feedback and dispatches custom events.
3. Monster spawner palette allows dragging token prototypes onto valid grid cells emitting `@token-spawn-requested`.
4. Storybook stories authored for all GM tools with full keyboard and mouse accessibility.
5. All TypeScript compilation and lint checks pass cleanly.
