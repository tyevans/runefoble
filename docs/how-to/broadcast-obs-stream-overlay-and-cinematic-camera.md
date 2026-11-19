# How-To: Broadcast with OBS Stream Overlay and Cinematic Director Auto-Camera

This guide explains how content creators and broadcast streamers (Devon) embed transparent party vitals HUD overlays into OBS / Streamlabs and configure the autonomous cinematic director camera without risking DM secret leaks (PRD-0011, US-0029, US-0030).

---

## 1. Adding the Party Vitals Overlay to OBS

Add one URL to OBS as a **Browser Source**. The App Shell serves the overlay on its own route. The page has no header and no shell chrome. Its background is transparent.

```
https://<your-host>/#/overlay/party-vitals/{session_id}?position=bottom&easing=cubic-bezier(0.25,0.1,0.25,1.0)&duration=300
```

### OBS Studio Configuration
1. In OBS Studio, add a new **Browser Source** to your tabletop scene.
2. Set **URL** to the address above. Replace `<your-host>` and `{session_id}`.
3. Set **Width** to `1920` and **Height** to `1080`.
4. Leave **Custom CSS** blank. The page sets its own transparent background.
5. The page needs a signed-in viewer. If the source shows a sign-in error, right-click the source, choose **Interact**, and sign in there.

### URL Query Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `position` | `string` | `bottom` | Layout: `bottom`, `top`, or `sidebar` |
| `easing` | `string` | `cubic-bezier(0.25, 0.1, 0.25, 1.0)` | CSS timing function for the card transitions. Only a `cubic-bezier(...)` value is accepted |
| `duration` | `integer` | `300` | Card transition duration in milliseconds (0 to 10000) |

A missing or malformed value takes its default. The values change how the overlay looks. They do not change what the owners send.

### Data Source

The page reads the party once from `GET /overlay/party-vitals/{session_id}?format=json`. The gateway checks `session.observe` on that read. The overlay then keeps itself current over its WebSocket. A viewer without `session.observe` sees an error on the page and no party data.

The gateway serves JSON only. A request for HTML from the gateway route gets `406` with `error: html_not_served`. Use the App Shell URL above for OBS.

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
