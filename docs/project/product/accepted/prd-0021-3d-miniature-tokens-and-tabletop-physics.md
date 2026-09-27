---
id: '0021'
title: 3D WebGL Tabletop Physics, Miniature Mini-Ragdolls & Kinetic Dice Collision
status: Accepted
created: 2026-09-26
---

# PRD-0021 — 3D WebGL Tabletop Physics, Miniature Mini-Ragdolls & Kinetic Dice Collision

## Who this is for

Content creators and tabletop streamers (like Devon), tactile adventurers (like Marcus), and expressive visual storytellers (like Nadia) who want combat encounters to feel visually spectacular, physical, and dramatic.

## What the person cannot do today

- Virtual tabletop tokens look like flat stickers sliding across a 2D checkerboard; there is no sense of physical presence, weight, or elevation.
- Digital dice rolling is reduced to instant numbers printed in a chat box, eliminating the shared communal suspense and tactile satisfaction of tumbling polyhedral dice.
- Critical hits, thunderwave explosions, and bull rushes produce only mechanical arithmetic rather than sending enemies physically tumbling back into walls or off cliff edges.
- Stream spectators experience visual boredom from sterile 2D map views, causing dead air during complex tactical encounters.

## What good looks like

1. **Kinetic 3D Rigid-Body Dice Simulation**:
   - Realistic polyhedral dice rolling in full 3D WebGL with mass, bounce friction, and angular momentum.
   - Tumbling dice bounce off dungeon walls, pillars, and miniature token bases before settling, accompanied by spatial audio dice tray clatter sounds.
   - Settled dice values match server-side cryptographic dice rolls 100% reliably.
2. **3D Miniature Tokens & Physical Bases**:
   - Stylized 3D miniature figurines with customizable weighted bases, snap-on condition rings (stunned, on fire, blessed), and elevation indicators.
   - Smooth token movement interpolation with physical momentum and banking along curved paths.
3. **Impact Knockback, Blast Waves & Mini-Ragdoll Physics**:
   - Powerful attacks, critical hits, and area-of-effect spells apply directional impulse forces to affected miniature tokens.
   - Miniatures slide across grid tiles with realistic friction damping and tumble down elevation ledges with balance recovery animations.
4. **Cinematic Director & Spectator Camera Orchestration**:
   - Automated camera system that dynamically tracks tumbling high-stakes dice (e.g., death saves, critical hits) and zooms into dramatic collision impacts for stream viewers.

## What this does not do

- It does not sacrifice tactical grid precision; miniature tokens always snap their logical game state to discrete grid coordinates once physics settlement completes.
- It does not exclude players with low-powered hardware; automatically downgrades to lightweight 2D canvas rendering if WebGL 2.0 or discrete GPU capabilities are insufficient.

## Checkable Outcomes

1. 3D physics engine resolves dice rolling and miniature collision simulations at steady 60fps on standard desktop browsers.
2. Dice simulation settlement agrees with cryptographic random number generation results on 100% of rolls.
3. Knockback impulse calculations displace miniature tokens across grid bounds and update board state positions within 50ms of physics resting state.
4. WebGL canvas memory footprint remains stable (<150MB GPU VRAM) over 4-hour extended combat sessions with zero memory leaks.

## Linked User Stories
- [`US-0061: 3D Miniature Tokens & WebGL Tabletop Physics`](../../user_stories/accepted/us-0061-3d-miniature-tokens-and-tabletop-physics.md)
- [`US-0029: Spectator Dynamic Cinematic Auto-Camera`](../../user_stories/accepted/us-0029-spectator-dynamic-cinematic-auto-camera.md)

## Implementing Backlog Tasks
- [`TASK-0150: Tabletop 3D Physics Engine & Mesh Collision Integration`](../../backlog/complete/0150-tabletop-3d-physics-engine-and-mesh-collision-enabler.md)
- [`TASK-0142: 3D Miniature Tokens & WebGL Tabletop Physics`](../../backlog/complete/0142-3d-miniature-tokens-and-webgl-physics.md)
- [`TASK-0170: Kinetic 3D Dice Physics and Tray Audio Integration`](../../backlog/proposed/0170-kinetic-3d-dice-physics-and-tray-audio.md)
- [`TASK-0171: Miniature Knockback Impulse and Elevation Physics`](../../backlog/proposed/0171-miniature-knockback-and-elevation-fall-physics.md)
