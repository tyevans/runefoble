# How-To: Interact with Tactile Board Kinematics and Spoken Ghost Previews

This guide explains how to use tactile token kinematics, interactive 5-foot route measuring, and real-time spoken ghost previews in the Runefoble tactical board microfrontend (`<runefoble-board>`).

---

## 0. Set Up the Session Battlemap

A new session has no board. The live session view shows `<runefoble-board-empty>` ("No battlemap yet") in the board area until the DM sets up the board (TASK-0906, TASK-0922, TASK-0928).

To set up the board as the DM:

1. Launch the session from the lobby.
2. In the board area, click **Set up battlemap**. Only a caller with the `run_session` capability sees this control. A player sees the empty state only.
3. The control sends one set-up call, `POST /api/v1/boards`. The body holds the default 10 x 10 grid and one `pc` token for each seated character (`tokens`, each with `character_id`). The tokens go to free start cells in seat order, in row order from the top-left cell (`startCells`).
4. The gateway creates the board. Then it places the tokens in list order through board_state.
5. After the last token call, the gateway sends the `board_ready` frame once to every socket of the session. Thus a client that reads the board after that frame gets the party tokens (TASK-0928). The App Shell of the DM reads the board from the server. A client cannot send `board_ready` (`UNKNOWN_FRAME`). Each other client that shows no board reads the board again.

`board_state` checks each call. The DM needs `campaign.run_session` to create the board. A character token needs `character.edit` on the character, so the character must belong to the campaign. The DM holds `character.edit` through `campaign->run_session`.

If a call fails:

- The board create fails (for example `403` or `503`): the control shows the server message. No board exists. The gateway sends no frame, and the client changes nothing.
- A token place fails after the board exists: the gateway stops at that token. It still sends `board_ready` once, because the board exists. The reply has the status of the failed call and the body `{"detail": "<token name>: <server message>", "token", "board_created": true, "upstream"}`. The App Shell shows the message in a toast and reads the board from the server. The board then shows the tokens that were placed.

The flow code is `setUpSessionBoard` in `services/board_state/ui/src/board-setup.ts`. The gateway code is `set_up_board` in `gateway/api/src/gateway_api/board_setup.py`.

### Placed Tokens Arrive Live

The ingress sends `/ws/boards/...` to `board-state:8002`, which owns the board socket (TASK-0928). Each token placed through `POST /api/v1/boards/{session_id}/tokens` goes to every open board socket of the session as one frame: `{"type": "token_placed", "session_id", "token": <PlacedTokenState>}`. `<runefoble-board>` adds the token to its list, or replaces a token with the same id. A refused placement sends no frame. A forged or uploaded map is applied to an existing board (the map switcher or the UVTT import). Set up the board first.

## 1. Tactile Token Kinematics & Drag-and-Drop

When dragging a miniature or token across the tactical board:
1. **Inertia & Elevation**: Tokens elevate visually with spring dampening and a raised drop shadow (`z-index: 100`, scale: 1.18).
2. **Snap-to-Grid Collision**: When the pointer is released, the token snaps smoothly to the nearest valid cell center and dispatches the standard `move-token` event with `{ tokenId, toX, toY }`. The board also sends the `confirm_move` action over its own socket, `/ws/boards/{session_id}` (see section 4.1). One drag sends one move. The browser click that ends the press stops at the token, so it sends no second move to the start cell. After a drag, no token is selected.
   - A tap on a token (press and release on the same cell) opens the radial menu. The menu stays open until you click a cell or pick an action.
3. **Dynamic Distance Ruler**: While dragging, a floating Bauhaus distance badge displays the cumulative travel distance in 5-foot increments.

---

## 2. Terrain & Hazard Awareness

The tactical board automatically evaluates terrain conditions along the movement trajectory:
- **Difficult Terrain**: Highlighted with an amber diagonal hatch and badge (`▲ +5ft`). Each difficult terrain cell adds a +5-foot movement penalty (costing 2 points of movement budget).
- **Loot Tokens**: An approved audience item drop places a loot token (`token_type: "loot"`) on its cell. The token shows the item name. It is not a combatant, and it does not block movement. A player token can move onto its cell.
- **Hazard Cells**: Highlighted with a warning border and flashing red background. A route that crosses a hazard cell alerts the player and Dungeon Master, even when the token lands on a cell without a hazard (e.g. `⚠️ Lava (2d10)`). The dice match the dice that the move applies. The board table gives acid `2d6`, spikes `2d4`, poison `1d4`, lava `2d10`, fire `1d6`, deep_water `1d6`, chasm `3d6`, and arcane_void `2d8`.

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
- `move-rejected`: `{ tokenId: string, toX: number, toY: number, reason: string }`. Emitted when the board socket is not open, so no `confirm_move` was sent. The board also shows `reason` in its alert line.

### Refused Moves

The board shows a refused action in an alert line (`role="alert"`) above the grid:
- The server answers a refused message with an `error` frame (see "WebSocket `/ws/boards/{session_id}`"). The board shows `<action> refused: <message>`. The token stays on its cell, because only a `token_moved` frame moves it.
- When the board socket is not open, the board shows "The board connection is not open, so the move was not sent."
- The next move clears the alert line.

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
- The first frame is `connected`. It carries `tokens`, a map of token id to PlacedTokenState at subscribe time. `<runefoble-board>` replaces its token list with this snapshot. Thus a screen that read the board before its socket opened still shows a move that another player made in between.
- `confirm_move`, `token_action`, and `radial_action` need `board_token.move` on `token_id`.
- A confirmed move broadcasts a `token_moved` frame. The frame has the same move fields as the HTTP move response: `movement_cost`, `hazard_triggered`, `damage_dice`, `trap_triggered`, and `movement_paused`. A move onto a trap stops at the trap cell and sets `movement_paused` to `true`.
- `aoe_place`, `cast_spell`, `spell_vfx`, `SpellCast`, and spoken spell intents need `campaign.play`.
- Every other defined message (previews, `aoe_preview`, `aoe_evaluate`, `cancel_preview`) needs `board.view`.
- A denied message returns `{"type": "error", "code": "PERMISSION_DENIED", "message": "...", "status": 403, "session_id": "...", "action": "confirm_move", "token_id": "..."}`. Every error frame names the `action` and the `token_id` of the refused message (`token_id` is `null` when the message has none). The socket stays open.
- A message type that the board does not define returns `UNKNOWN_ACTION`. The board no longer rebroadcasts client frames.
- A `confirm_move` without `token_id`, `to_x` or `to_y` returns `INVALID` (`422`) with a message that names the missing fields. A move that the board refuses (for example out of bounds, or over the movement budget) also returns `INVALID`. No message is dropped without a frame.
- An unexpected server error closes the socket with `1011` and logs the error.

### Client side

`<runefoble-board>` reads the token from the App Shell `runefoble-auth` context (`@runefoble/ui-core`). It opens the socket with `boardSocketProtocols(token)`. `<runefoble-dm-trap-controls>` and `<runefoble-map-switcher>` send `Authorization: Bearer` from the same context. They no longer send a `campaign_id` query.

### App Shell mount

The App Shell mounts `<runefoble-board>` only after the board read of the open session returns a board. Until the first read answers, the board area shows "Loading the battlemap..." (`boardKind` is `loading`). Thus no board socket opens before the board exists, and each page has one board socket: the one of `<runefoble-board>` (`getWebSocketUrl()` in `runefoble-app.ts` only builds its URL). A `board_ready` frame reads the board again while the shell has no board or the first read is still out. A board read replaces the shown token cells with the server cells.

The App Shell mounts `<runefoble-dm-trap-controls>` and `<runefoble-map-switcher>` in the live tabletop view (`#/campaigns/:campaignId/sessions/:sessionId`). Only a caller with the `run_session` capability (from `GET /api/v1/campaigns/{campaign_id}/capabilities`) sees them. Both take the session id as `boardId`. A `move-token` dispatch from `<runefoble-board>` sets `targetX` and `targetY` on `<runefoble-dm-trap-controls>` to the destination cell. A `map-switched` event reloads the board from the server.

The App Shell does not load the battlemap list yet. `<runefoble-map-switcher>` therefore shows an empty grid. Loading battlemaps for the switcher is a follow-up.
