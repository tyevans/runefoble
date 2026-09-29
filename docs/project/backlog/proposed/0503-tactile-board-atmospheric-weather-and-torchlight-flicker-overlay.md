---
id: '0503'
title: Tactile Board Atmospheric Weather Particles and Torchlight Flicker Overlay
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0004
- TASK-0104
- TASK-0132
governing_adrs:
- ADR-0004
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0013
governing_stories:
- US-0042
- US-0043
target_release: 0.9.0
---

# TASK-0503: Tactile Board Atmospheric Weather Particles and Torchlight Flicker Overlay

## Status
Proposed

## Summary
Implement a high-performance 2D/WebGL canvas overlay layer for `<runefoble-board>` (`services/board_state/ui/src/`) that renders dynamic torchlight flicker around light-emitting tokens and ambient weather particles (rain, falling embers, crypt mist) with configurable density and wind velocity, delivering living tactical map immersion while maintaining a consistent 60fps frame rate without impacting token drag-and-drop kinematics per PRD-0013.

## Problem Statement
While the tactical board renders grid cells, tokens with kinetic spring dampening, and line-of-sight fog-of-war shrouds, the battlemaps remain visually static. PRD-0013 specifies that virtual tabletop environments should feel alive with dynamic torchlight flicker, weather particles (rain streaks, embers floating from campfires, crypt mist rolling across the floor), and seamless shroud exploration. Without this atmospheric layer, scenes lack cinematic presence and depth during exploration and combat encounters.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Encapsulate canvas overlays within the Lit Shadow DOM with reactive property bindings.
- **ADR-0012: CSS Custom Properties & Bauhaus Design Tokens**: Honor visual accessibility, high-contrast modes, and performance toggles.
- **ADR-0013: Frontend Microfrontend Architecture**: Keep presentation logic cleanly contained in `services/board_state/ui/` with zero backend coupling.

## Product & User Story References
- [`prd-0013-immersive-and-intuitive-frontend-experience.md`](../../product/accepted/prd-0013-immersive-and-intuitive-frontend-experience.md)
- [`us-0043-tactile-kinetic-board-and-spoken-ghost-previews.md`](../../user_stories/accepted/us-0043-tactile-kinetic-board-and-spoken-ghost-previews.md)

## Scope of Work
1. **Atmospheric Canvas Renderer (`services/board_state/ui/src/weather_canvas.ts`)**:
   - Particle emitter system supporting archetypes: `rain` (slanted precipitation streaks), `embers` (rising glowing flecks with brownian motion), and `mist` (slow-drifting radial alpha puffs).
   - Torchlight flicker generator: Computes Perlin noise or sinusoidal modulation of torch radii around designated light-source tokens (`torch_radius`, `flicker_intensity`, `color_temp`).
2. **Board Component Integration (`services/board_state/ui/src/runefoble-board.ts`)**:
   - Add `@property({ type: String }) weather: 'none' | 'rain' | 'embers' | 'mist' = 'none'`.
   - Add `@property({ type: Boolean }) dynamicLighting: boolean = true`.
   - Mount atmospheric canvas overlay above the battlemap texture but beneath interactive token handles.
   - Respect `prefers-reduced-motion` and low-power hardware modes by reducing particle counts or pausing animations.
3. **Storybook Stories & Visual Controls (`services/board_state/ui/src/runefoble-board.stories.ts`)**:
   - Add Storybook variations showcasing rain over cavern maps, embers near campfires, and spooky crypt mist.

## Definition of Done
1. `weather_canvas.ts` implemented with particle recycling and zero per-frame heap allocations.
2. Torchlight flicker and ambient weather modes render smoothly at 60fps on standard desktop and tablet browsers.
3. Component respects `prefers-reduced-motion` and disables particle loops when `weather="none"`.
4. Storybook stories authored demonstrating all weather and lighting configurations.
5. All TypeScript compilation (`npm run check`) and lint checks pass cleanly.
