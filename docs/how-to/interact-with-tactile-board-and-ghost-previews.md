# How-To: Interact with Tactile Board Kinematics and Spoken Ghost Previews

This guide explains how to use tactile token kinematics, interactive 5-foot route measuring, and real-time spoken ghost previews in the Runefoble tactical board microfrontend (`<runefoble-board>`).

---

## 1. Tactile Token Kinematics & Drag-and-Drop

When dragging a miniature or token across the tactical board:
1. **Inertia & Elevation**: Tokens elevate visually with spring dampening and a raised drop shadow (`z-index: 100`, scale: 1.18).
2. **Snap-to-Grid Collision**: When the pointer is released, the token snaps smoothly to the nearest valid cell center and dispatches the standard `move-token` event with `{ tokenId, toX, toY }`. The board also sends the `confirm_move` action over its own socket, `/ws/boards/{session_id}` (see section 4.1).
3. **Dynamic Distance Ruler**: While dragging, a floating Bauhaus distance badge displays the cumulative travel distance in 5-foot increments.

---

## 2. Terrain & Hazard Awareness

The tactical board automatically evaluates terrain conditions along the movement trajectory:
- **Difficult Terrain**: Highlighted with an amber diagonal hatch and badge (`▲ +5ft`). Each difficult terrain cell adds a +5-foot movement penalty (costing 2 points of movement budget).
- **Hazard Cells**: Highlighted with a warning border and flashing red background. Landing on a hazard alerts the player and Dungeon Master (e.g. `⚠️ Lava (2d10)`).

```typescript
// Example terrain configuration
const terrainCells = [
  { x: 3, y: 2, terrainType: 'difficult' },
  { x: 5, y: 4, terrainType: 'normal', hazard: 'lava' },
];
```

---

## 3. Spoken Ghost Previews & WebSocket Synchronization

Per PRD-0013 and US-0043 ("Speak and the board obeys"), spoken voice actions staged by The Watcher or players generate a real-time preview before committing to persistent game state:

1. **Sub-200ms Latency**: The board microfrontend receives `SpeechIntentParsed` or `ghost_preview` events over WebSocket frontdoors (`/ws/boards/{session_id}` or `/ws/campaigns/{campaign_id}`).
2. **Visual Staging Reticle**:
   - A semi-transparent ghost token (50% opacity with a pulsing Bauhaus accent ring) appears at the destination coordinates.
   - An animated dashed targeting vector line connects the origin cell to the destination with an arrowhead reticle.
3. **Commit or Discard**:
   - **Confirm**: Click the ghost token directly, or click the **"✓ Confirm Move"** button in the floating ghost banner. This commits the action and publishes `TokenMoved` / updates persistent state.
   - **Cancel**: Click **"✕ Cancel"** or let the 15-second countdown timer expire to rollback the preview without mutating board coordinates.

---

## 4. Programmatic API & Events

```html
<runefoble-board
  .cols="${8}"
  .rows="${8}"
  .tokens="${tokens}"
  .terrainCells="${terrainCells}"
  .activeGhost="${ghostPreviewState}"
  @move-token="${(e) => handleTokenMove(e.detail)}"
  @confirm-ghost="${(e) => handleConfirmGhost(e.detail)}"
  @cancel-ghost="${(e) => handleCancelGhost(e.detail)}"
></runefoble-board>
```

### Emitted Custom Events:
- `move-token`: `{ tokenId: string, toX: number, toY: number }`
- `confirm-ghost`: `{ ghost: GhostPreviewState }`
- `cancel-ghost`: `{ ghost: GhostPreviewState }`
- `ghost-timeout`: `{ tokenId: string }`
- `move-rejected`: `{ tokenId: string, toX: number, toY: number, reason: string }`. Emitted when the board socket is not open, so no `confirm_move` was sent.

### 4.1 Event-to-Route Table

Each board UI event maps to one public route or socket action. The owning component renders the server response. It does not show an optimistic result (TASK-0563).

| UI event | Owning component | Backend call | Success signal |
|---|---|---|---|
| `move-token` (drag release, cell click, ghost confirm) | `<runefoble-board>` | WebSocket `/ws/boards/{session_id}`, action `confirm_move` with `{ token_id, to_x, to_y, initiated_by: "player" }` | Server broadcasts `token_moved`. The board updates the token position. |
| `trap-placed` (emitted by Arm Cell) | `<runefoble-dm-trap-controls>` | `POST /api/v1/boards/{board_id}/traps?campaign_id=...` | HTTP 201. Event detail is the server trap state. |
| `map-switched` (emitted by Teleport Here) | `<runefoble-map-switcher>` | `POST /api/v1/boards/{board_id}/switch-map?campaign_id=...` | HTTP 2xx. Event detail is the server switch response. |
| `open-map-switcher` (Switch Map button) | `<runefoble-dm-trap-controls>` | None. UI only. | Host opens `<runefoble-map-switcher>`. |

On a non-2xx response, Arm Cell and Teleport Here show the server `detail` text. They do not emit a success event.

Set `boardId` and `campaignId` on both DM components. Set `targetX` and `targetY` on the trap controls before Arm Cell. Without a target cell, Arm Cell does not send a request.

---

## 5. Storybook Verification

Inspect and test all kinetic behaviors and preview states interactively in Storybook:

```bash
pnpm run storybook
```

Stories available in `TTRPG/RunefobleBoard`:
1. **TokenKinematicsAndMeasurement**: Drag tokens across normal and difficult terrain to inspect live 5-ft ruler calculations.
2. **SpokenGhostPreviewWithConfirmation**: Interactive ghost preview with dashed targeting line and confirmation tap.
3. **GhostCancellationAndTimeout**: Auto-expiring ghost preview demonstrating timeout rollback.
