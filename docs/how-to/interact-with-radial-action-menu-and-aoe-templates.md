# How to Interact with Radial Token Action Menu & Rotatable AoE Spell Templates

This how-to guide demonstrates how to invoke one-tap tactical combat actions (Attack, Dash, Disengage, Dodge, Cast) using the contextual radial action menu and position rotatable geometric Area of Effect (AoE) spell templates with real-time target intersection highlighting.

---

## 1. Invoking Contextual Radial Token Actions

When a player or DM clicks or taps a character token without dragging, the `<runefoble-radial-menu>` blooms outward in under 120ms with Bauhaus geometric icons.

### 1.1 Web Component Integration

The radial menu is vendored in `@runefoble/board-state-ui` and seamlessly integrated into `<runefoble-board>`:

```html
<runefoble-board
  .cols=${10}
  .rows=${10}
  .tokens=${tokens}
  @token-action=${(e) => handleTokenAction(e.detail)}
></runefoble-board>
```

When an action is chosen, `<runefoble-board>` emits a `token-action` CustomEvent:

```typescript
board.addEventListener('token-action', (event) => {
  const { tokenId, action, details } = (event as CustomEvent).detail;
  console.log(`Token ${tokenId} executed ${action}`);
});
```

### 1.2 Executing Token Actions via HTTP Frontdoor

You can also trigger token combat actions directly via the Board State microservice HTTP API:

```bash
curl -X POST http://localhost:8002/api/v1/boards/session-alpha/tokens/valeros/action \
  -H "Content-Type: application/json" \
  -d '{
    "action": "dodge",
    "initiated_by": "player"
  }'
```

Response payload:
```json
{
  "token_id": "valeros",
  "action": "dodge",
  "status": "executed",
  "target_token_ids": [],
  "details": {},
  "message": "Action 'dodge' successfully executed for token valeros"
}
```

### 1.3 Modular Radial Architecture (ADR-0004, ADR-0012, ADR-0013)

Under ADR-0004, ADR-0012, and ADR-0013, the radial action menu is decomposed into decoupled submodules under `services/board_state/ui/src/radial/`:
- `radial_menu.styles.ts`: Bauhaus Lit CSS styles for circular radial container, bloom animations, action wedge transitions, and action badges (< 90 lines).
- `radial_glyphs.ts`: Pure Bauhaus SVG glyph rendering functions for tactical combat actions (< 100 lines).
- `radial_wedge.ts`: Polar coordinate mathematics (`polarToCartesian`, `describeArc`), circular wedge positioning calculations, and Lit HTML wedge template (< 90 lines).
- `radial_menu.ts`: Component controller `<runefoble-radial-menu>` coordinating action selection and lifecycle events (< 100 lines).

---

## 2. Positioning and Rotating AoE Spell Templates

Selecting the **Cast** action on the radial menu (or triggering spell casting mode) mounts the `<runefoble-aoe-template>` overlay over the tactical grid.

### 2.1 Supported Geometric Shapes

| Shape | Standard Sizes | Angular Spread / Width | Calculation |
|---|---|---|---|
| **Cone** | 15 ft, 30 ft | 53.13° spread angle | Distance $\le$ radius, angular delta $\le$ 26.565° |
| **Sphere** | 10 ft, 20 ft radius | Full 360° circle | Euclidean distance $\le$ radius |
| **Line** | 5 ft $\times$ 30 ft, 5 ft $\times$ 60 ft | 5 ft width | Projection along vector $\le$ length, perpendicular $\le$ width/2 |
| **Cube** | 10 ft, 20 ft, 30 ft side | Rotatable square | Projection along oriented axes $\le$ size/2 |

### 2.2 Tactile 15-Degree Angle Snapping

Drag the circular rotation handle positioned at the apex of the template. The rotational engine automatically snaps angles to 15-degree increments:

```typescript
import { snapAngle } from '@runefoble/board-state-ui';

const snappedAngle = snapAngle(rawAngleDegrees, 15);
```

### 2.3 Real-Time Token Intersection Highlighting

Tokens enclosed within the template geometry are highlighted at 60fps with glowing targeting halos (`.target-halo`), and affected grid cells receive semi-transparent spell tint (`.aoe-affected-cell`):

```typescript
import { computeAffectedTokens, computeAffectedCells } from '@runefoble/board-state-ui';

const affectedTokenIds = computeAffectedTokens(tokens, aoeConfig);
const affectedCells = computeAffectedCells(cols, rows, aoeConfig);
```

### 2.4 Modular Architecture (ADR-0013)

Under ADR-0013 and Hard Invariant 6, the AoE template engine is organized into focused, decoupled TypeScript modules under `services/board_state/ui/src/`:
- `aoe_types.ts`: Type contracts, shape enums, handle event signatures, and design system color tokens (< 80 lines).
- `aoe_geometry.ts`: Pure mathematical intersection algorithms for cones, spheres, lines, and cubes (< 150 lines).
- `aoe_canvas.ts`: SVG path builders, dashed outlines, pulse keyframes, and rotational handles (< 150 lines).
- `aoe_templates.ts`: Coordinator facade and `<runefoble-aoe-template>` Custom Element lifecycle (< 100 lines).

---

## 3. Real-Time Streaming via WebSockets

All radial action invocations and live AoE rotations stream over `/ws/boards/{session_id}`.

### 3.1 Live AoE Preview Stream

Send an `aoe_preview` payload:
```json
{
  "action": "aoe_preview",
  "shape": "cone",
  "origin_x": 2.5,
  "origin_y": 2.5,
  "direction_deg": 45.0,
  "radius_ft": 15.0,
  "spell_name": "Burning Hands"
}
```

The server broadcasts the evaluated targets to all connected peers:
```json
{
  "type": "aoe_preview",
  "session_id": "session-alpha",
  "template": {
    "shape": "cone",
    "direction_deg": 45.0,
    "affected_token_ids": ["goblin-1", "goblin-2"],
    "affected_cells": [[2, 2], [3, 2], [3, 3]]
  }
}
```

### 3.2 Confirming AoE Spell Placement

When the caster taps **✓ Confirm Cast**, an `aoe_place` payload is transmitted, persisting the template on the board aggregate and emitting the domain event `AoETemplatePlaced`.

---

## 4. Verification

Run the blackbox test suite to verify end-to-end functionality:
```bash
uv run pytest tests/test_blackbox_radial_menu_and_aoe.py
```
