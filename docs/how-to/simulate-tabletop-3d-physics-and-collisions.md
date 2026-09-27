# How-To: Simulate Tabletop 3D Physics and Mesh Collisions

This guide explains how to use the deterministic 3D physics and mesh collision simulation engine in Runefoble (`services/board_state/src/board_state/physics/`) for tumbling physical dice and miniature token knockback impulses.

---

## 1. Overview & Physics Architecture

Per **US-0061** and **PRD-0013**, Runefoble supports 3D rigid-body simulation on the tactical battlemap:
- **Collision Shapes**: Axis-aligned 3D bounding boxes for table perimeters (`BoundingBox3D`), upright cylindrical collision meshes for miniature token bases (`BoundingCylinder`), and elevation step grids (`HeightfieldTerrain`).
- **Tumbling Dice Ballistics**: Simulates parabolic trajectories, air resistance, restitution bounces on floor/walls, and surface friction damping until resting face values settle.
- **Token Knockback & Impulse Slide**: Applies directional impulses to miniature tokens, calculating drag and halting upon collision with high-elevation walls or obstacles.
- **Domain Event Streaming**: Emits `runefoble.events.board.physics.collision` and `runefoble.events.board.dice.settled` over Redis Streams and updates `BoardStateAggregate`.

---

## 2. Simulating a 3D Tumbling Dice Throw

To throw physical tumbling dice across terrain with floor and wall bounces:

```bash
POST /api/v1/boards/{board_id}/physics/simulate-throw
Content-Type: application/json

{
  "dice_type": "d20",
  "origin_x": 1.0,
  "origin_y": 1.0,
  "origin_z": 2.5,
  "velocity_x": 4.0,
  "velocity_y": 4.0,
  "velocity_z": 2.0,
  "restitution": 0.5,
  "friction": 0.3,
  "seed": 42
}
```

### Response
```json
{
  "dice_id": "dice-78ab3e4c",
  "dice_type": "d20",
  "face_value": 17,
  "settled_x": 3.84,
  "settled_y": 3.65,
  "settled_z": 0.0,
  "settled_cell": [3, 3],
  "bounces": 4,
  "trajectory": [
    { "x": 1.0, "y": 1.0, "z": 2.5, "t": 0.0 },
    { "x": 1.16, "y": 1.16, "z": 2.56, "t": 0.04 }
  ],
  "status": "settled"
}
```

The simulation dispatches a `DiceSettled` event to the board event store and publishes it via Redis Streams (`runefoble.events.board`).

---

## 3. Applying Token Knockback Against Walls

When an attack or shockwave inflicts physical knockback on a miniature token:

```bash
POST /api/v1/boards/{board_id}/physics/knockback
Content-Type: application/json

{
  "token_id": "fighter-1",
  "direction_x": 1.0,
  "direction_y": 0.0,
  "distance_ft": 20.0,
  "mass": 2.0
}
```

### Response (Collision Halting)
```json
{
  "token_id": "fighter-1",
  "from_x": 2,
  "from_y": 3,
  "to_x": 3,
  "to_y": 3,
  "settled_position": [3, 3],
  "distance_traveled_ft": 8.0,
  "collided": true,
  "collision_type": "wall",
  "collision_point": [3.8, 3.0, 3.0],
  "impact_energy": 28.12,
  "trajectory": [...],
  "status": "settled"
}
```

If the token encounters a high-elevation step (`Δ elevation > 0.5`) or obstacle along the ray, the trajectory halts immediately at the impact point, records a `PhysicsCollisionOccurred` event with calculated impact energy (`0.5 * mass * v²`), and snaps the miniature token to the nearest accessible cell center.

---

## 4. Subscribing to Physics Events via WebSocket

Clients connected to `/ws/boards/{session_id}` receive real-time physics telemetry:

```json
{
  "type": "token_knockback",
  "action": "knockback",
  "status": "settled",
  "knockback": {
    "token_id": "fighter-1",
    "collided": true,
    "collision_type": "wall",
    "impact_energy": 28.12
  }
}
```

---

## 5. Client-Side 3D Miniature Tokens & Tabletop WebGL Canvas

The frontend microfrontend in `@runefoble/board-state-ui` provides client-side WebGL rendering for 3D miniature figurines, tumbling dice, and elevation cliffs:

### Embedding `<runefoble-tabletop-3d>`

```html
<runefoble-tabletop-3d
  .cols="${8}"
  .rows="${8}"
  .tokens="${tokens}"
  .terrainCells="${terrain}"
  theme="dark"
></runefoble-tabletop-3d>
```

### Enabling 3D in `<runefoble-board>`

`<runefoble-board>` features an integrated 3D toggle layer:

```typescript
// Enable 3D mode programmatically or tap the '🎲 3D Mode: ON' header toggle
board.enable3D = true;

// Trigger client-side dice roll or knockback animation
board.roll3DDice({ faceValue: 20, settledCell: [3, 3] });
board.knockbackToken({ tokenId: 'fighter-1', fromX: 2, fromY: 3, toX: 4, toY: 3 });
```

### Components and Architecture

- **`miniature_mesh.ts`**: Extrudes circular 2D tokens into stylized 3D miniature bases with character portraits, health pips, and snap-on condition rings (e.g., stunned, on fire, blessed).
- **`tabletop_canvas.ts`**: WebGL/Canvas visualizer driving 60fps polyhedral dice tumbling, wall collisions, and ragdoll tilt balance recovery.
- **`physics_bridge.ts`**: Handles bidirectional WebSocket events (`dice_settled`, `token_knockback`) and triggers backend simulation endpoints.
- **`dice_models.ts`**: Parametric polyhedral collision geometries for d4, d6, d8, d10, d12, and d20 dice with calibrated restitution, center of mass, and friction parameters.
- **`tray_audio.ts`**: WebAudio synthesis and foley player triggering velocity-scaled acoustic impacts on board perimeters and obstacle collision contacts.
- **`dice_solver.ts`**: Deterministic trajectory and rotational momentum solver guaranteeing resting face values conform 100% to server-side cryptographic rolls.
- **`knockback_solver.ts`**: Directional impulse vector solver calculating mass scaling, deceleration sliding friction, and obstacle collision rebounds.
- **`elevation_fall.ts`**: Raycast heightfield collision dropping miniatures down vertical elevation steps with rotational tilt damping and upright balance recovery.
- **`grid_snapper.ts`**: Discrete board grid snapper aligning miniature tokens to board grid centers within 50ms of physics settlement.

---

## 6. Kinetic 3D Dice Tray & Synchronized Acoustic Clatter

The `<runefoble-dice-tray-3d>` component provides an encapsulated 3D dice tray with physical rigid-body tumbling, perimeter wall bounces, and real-time WebAudio synthesis:

```html
<runefoble-dice-tray-3d
  .width="${500}"
  .height="${300}"
  theme="dark"
></runefoble-dice-tray-3d>
```

```typescript
// Throw a d20 with server-side cryptographic alignment
const tray = document.querySelector('runefoble-dice-tray-3d');
tray.roll('d20', 20, { velocity: { x: 6.2, y: 5.1, z: 2.2 } });

// Multi-dice toss across full polyhedral set
tray.rollMultiple([
  { diceType: 'd4', targetFaceValue: 4 },
  { diceType: 'd6', targetFaceValue: 6 },
  { diceType: 'd8', targetFaceValue: 8 },
  { diceType: 'd10', targetFaceValue: 10 },
  { diceType: 'd12', targetFaceValue: 12 },
  { diceType: 'd20', targetFaceValue: 20 },
]);

// Listen for acoustic impact and settlement events
tray.addEventListener('tray-audio-played', (e) => {
  console.log('Impact sound:', e.detail.impactType, e.detail.velocity);
});
tray.addEventListener('dice-settled', (e) => {
  console.log('Dice settled on face:', e.detail.faceValue);
});
```

---

## 7. Directional Miniature Knockback, Elevation Ledge Drops & Grid Snapping

For kinetic token combat impacts (bull rushes, thunderwaves, and repelling blasts):

### Solving Knockback Trajectory Client-Side

```typescript
import {
  solveKnockbackTrajectory,
  solveElevationFall,
  scheduleGridSnap,
} from '@runefoble/board-state-ui';

// 1. Calculate directional knockback impulse with mass scaling and sliding friction
const knockback = solveKnockbackTrajectory({
  tokenId: 'fighter-1',
  fromX: 2,
  fromY: 3,
  directionX: 1.0,
  directionY: 0.0,
  distanceFt: 15.0,
  mass: 1.0,
  friction: 0.35,
  restitution: 0.3,
  walls: [{ x: 5, y: 3 }],
});

// 2. If token drops off an elevation step, resolve vertical gravity fall & upright balance recovery
if (knockback.toZ < currentElevation) {
  const fall = solveElevationFall({
    tokenId: 'fighter-1',
    fromZ: currentElevation,
    targetZ: knockback.toZ,
    gravity: 14.0,
    tiltDamping: 7.0,
  });
  console.log('Landed safely upright:', fall.recoveredUpright);
}

// 3. Snap continuous resting position to discrete board grid centers within 50ms
await scheduleGridSnap({
  tokenId: 'fighter-1',
  rawX: knockback.toX,
  rawY: knockback.toY,
  rawZ: knockback.toZ,
}, (snap) => {
  console.log(`Snapped to cell [${snap.snappedCell}] in ${snap.settledInMs}ms (<= 50ms: ${snap.syncedWithin50ms})`);
});
```



