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
- **Hazard Cells**: Highlighted with a warning border and flashing red background. A route that crosses a hazard cell alerts the player and Dungeon Master, even when the token lands on a cell without a hazard (e.g. `⚠️ Lava (2d10)`). The dice match the dice that the move applies. The board table gives acid `2d6`, spikes `2d4`, poison `1d4`, lava `2d10`, and fire `1d6`.

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

1. **Sub-200ms Latency**: The board microfrontend receives a `ghost_preview` message over the board socket (`/ws/boards/{session_id}`).
   - **Spoken move source (TASK-0814)**: The client calls `POST /api/v1/watcher/speak-and-act`. For a move, The Watcher proposes it to `board_state` at `POST /api/v1/boards/{session_id}/ghost-previews`, with the speaker's own bearer. The board stages the preview and broadcasts `ghost_preview` (`status: staged`) to every socket of the session. The proposal does not move the token.
   - **Manual preview**: A socket frame `ghost_preview` with `token_id`, `to_x`, and `to_y` stages the same preview.
2. **Visual Staging Reticle**:
   - A semi-transparent ghost token (50% opacity with a pulsing Bauhaus accent ring) appears at the destination coordinates.
   - An animated dashed targeting vector line connects the origin cell to the destination with an arrowhead reticle.
3. **Commit or Discard**:
   - **Confirm**: Click the ghost token directly, or click the **"✓ Confirm Move"** button in the floating ghost banner. The board sends `confirm_move`. Only this message commits the move. The board then publishes `runefoble.events.board.token_moved` and updates persistent state. No other path moves a token from speech.
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

## 6. Authorization

Every board route needs a verified bearer token. The board service checks one schema permission per action (ADR-0001). It never checks a role name.

| Action | Permission |
|---|---|
| Place a character token | `character.edit` on the character and `campaign.play` |
| Place any other token, import a map, place a light, decay decals | `board.manage_traps` |
| Move or remove a token, run a token action, knock a token back | `board_token.move` on the token, or `board.manage_traps` |
| Place or remove an AoE template, cast spell VFX, throw dice, toggle a door | `campaign.play` on the board campaign |
| Preview a move, evaluate an AoE, list templates, decals, doors, and lights | `board.view` |
| Read the board, one token, the visibility mask, or the trap list | `board.view` (`403` otherwise; secret layer still needs `board.view_secret_layer`) |

### How a token gets its tuples

The token placement route writes the tuples in the same request that saves the token. It writes `board_token:<id>#campaign@campaign:<cid>`. For a character token it also writes `board_token:<id>#character@character:<char_id>`. Removal deletes them. No stream consumer is involved. The `runefoble.events.board.token_placed` identity-sync consumer is not wired in any deployment and the board does not need it.

Token ids are global in SpiceDB. A token id must use only letters, digits, and `_ - = + | /`. The route returns `409` when another campaign already owns the id.

### WebSocket `/ws/boards/{session_id}`

- Offer the subprotocols `runefoble.v1` and `runefoble.bearer.<jwt>`. A missing or invalid token closes the handshake with `1008`. A user without `board.view` closes with `4403`, the code of the gateway session sockets. Both closes happen before accept.
- `confirm_move`, `token_action`, and `radial_action` need `board_token.move` on `token_id`.
- `aoe_place`, `cast_spell`, `spell_vfx`, `SpellCast`, and spoken spell intents need `campaign.play`.
- Every other defined message (previews, `aoe_preview`, `aoe_evaluate`, `cancel_preview`) needs `board.view`.
- A denied message returns `{"type": "error", "code": "PERMISSION_DENIED", "status": 403, "session_id": "..."}`. The socket stays open.
- A message type that the board does not define returns `UNKNOWN_ACTION`. The board no longer rebroadcasts client frames.
- An unexpected server error closes the socket with `1011` and logs the error.

### Client side

`<runefoble-board>` reads the token from the App Shell `runefoble-auth` context (`@runefoble/ui-core`). It opens the socket with `boardSocketProtocols(token)`. `<runefoble-dm-trap-controls>` and `<runefoble-map-switcher>` send `Authorization: Bearer` from the same context. They no longer send a `campaign_id` query.

### App Shell mount

The App Shell mounts `<runefoble-dm-trap-controls>` and `<runefoble-map-switcher>` in the live tabletop view (`#/campaigns/:campaignId/sessions/:sessionId`). Only a caller with the `run_session` capability (from `GET /api/v1/campaigns/{campaign_id}/capabilities`) sees them. Both take the session id as `boardId`. A `move-token` dispatch from `<runefoble-board>` sets `targetX` and `targetY` on `<runefoble-dm-trap-controls>` to the destination cell. A `map-switched` event reloads the board from the server.

The App Shell does not load the battlemap list yet. `<runefoble-map-switcher>` therefore shows an empty grid. Loading battlemaps for the switcher is a follow-up.
