# How-To: Broadcast with OBS Stream Overlay and Cinematic Director Auto-Camera

This guide explains how content creators and broadcast streamers (Devon) embed transparent party vitals HUD overlays into OBS / Streamlabs and configure the autonomous cinematic director camera without risking DM secret leaks (PRD-0011, US-0029, US-0030).

---

## 1. Reading the Party Vitals Overlay Data

The gateway serves the party vitals as JSON:

```
http://localhost:8000/overlay/party-vitals/{session_id}?format=json
```

The endpoint needs a verified `Authorization: Bearer <jwt>` header and the `session.observe` permission. The party and the camera target come from `board_state`. The round comes from `game_session`. A monster is never shown.

The gateway no longer serves an HTML page for this route (TASK-0823). A request with `format=html`, or an `Accept` header that asks only for `text/html`, gets `406` with `error: html_not_served`. The OBS browser source cannot send a bearer header, so it cannot use this route. Host the `<runefoble-spectator-overlay>` component in an App Shell route to show the overlay in OBS. That route is not built yet.

### URL Configuration Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `position` | `string` | `bottom` | Layout hint echoed in the JSON: `bottom`, `top`, or `sidebar` |
| `format` | `string` | none | `json` returns JSON. `html` returns `406` |

---

## 2. Owner-Side Redaction

Each owner removes private data before the gateway reads it:
- **`board_state`** (`GET /api/v1/boards/{session_id}/spectator`): monsters are dropped. Only the fields listed in the audience projection leave the owner. The `party` list holds the player characters with hit points.
- **`game_session`** (`GET /api/v1/sessions/{session_id}/spectator`): the session status, the combat round, the scene atmosphere, and the public chronicle. DM-only fields stay in the owner.
- **Gateway**: joins the two owner views. It adds no value and removes no field. A reply that does not match the wire model becomes `502`.

---

## 3. Autonomous Cinematic Director Camera

The camera target belongs to `board_state`. It is stored in the board aggregate as a `CameraFocused` event. A restart or a new gateway instance reads the same target.

The gateway relays each frame to the owner:
1. **Turn Started (`turn_started`)**: the gateway calls `POST /api/v1/boards/{session_id}/camera/turn-started` with the `token_id` or `character_id`. The owner centers the camera on that token.
2. **Action Centers (`token_moved`)**: the gateway calls `POST /api/v1/boards/{session_id}/camera/token-moved` with `token_id`, `to_x`, and `to_y`. The owner centers the camera on the destination.
3. **Dice rolls (`dice_rolled`)**: the gateway relays a `roll_animation` frame. It stores nothing.

The owners need `session.participate` for a camera change. A spectator who sends a camera frame gets `PERMISSION_DENIED` from the gateway. The gateway sends no frame to the room.

### WebSockets Integration

Connect to the spectator WebSocket feed at `ws://localhost:8000/ws/overlay/${sessionId}`. The gateway admits the handshake only with a verified bearer subprotocol. Tokens in the URL are refused. The caller needs `session.observe` on the session. Otherwise the gateway closes the socket with code `4403`. A client that sends frames (`turn_started`, `token_moved`, `dice_rolled`) needs `session.participate`.

The gateway validates each frame before it acts. These error frames keep the socket open:

| Code | Meaning |
|---|---|
| `PERMISSION_DENIED` | The sender lacks `session.participate` |
| `INVALID_FRAME` | The frame does not match the schema (for example `result` is not a number) |
| `CAMERA_REJECTED` | The board owner refused the focus (for example, the token is not on the board) |
| `CAMERA_UNAVAILABLE` | The board owner did not answer. The room gets nothing |

```javascript
const ws = new WebSocket(`ws://localhost:8000/ws/overlay/${sessionId}`, [
  "runefoble.v1",
  `runefoble.bearer.${accessToken}`,
]);

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  if (msg.type === "camera_target_updated") {
    console.log("Auto-Camera Target:", msg.camera.target_x, msg.camera.target_y, msg.camera.zoom);
  } else if (msg.type === "roll_animation") {
    console.log("Dice Roll Animation:", msg.roller_name, msg.dice_formula, msg.result);
  }
};
```

The path `/overlay/ws/{session_id}` was removed (TASK-0823). Use `/ws/overlay/{session_id}`. The path `/ws/spectator/{session_id}` remains and serves the same feed.

## 4. Microfrontend Component Usage

The `<runefoble-spectator-overlay>` element is vendored by `services/game_session/ui/`:

```html
<script type="module" src="/services/game_session/ui/src/runefoble-spectator-overlay.ts"></script>

<runefoble-spectator-overlay
  session-id="camp-101"
  position="bottom"
  transparent-mode
  connect-ws
></runefoble-spectator-overlay>
```

The overlay reads the bearer token from the App Shell auth context. Without a signed-in session it does not open the socket. It shows a status line instead.
