# How-To: Broadcast with OBS Stream Overlay and Cinematic Director Auto-Camera

This guide explains how content creators and broadcast streamers (Devon) embed transparent party vitals HUD overlays into OBS / Streamlabs and configure the autonomous cinematic director camera without risking DM secret leaks (PRD-0011, US-0029, US-0030).

---

## 1. Embedding the OBS Transparent Party HUD

The gateway provides a dedicated browser source endpoint serving an alpha-transparent canvas (`rgba(0, 0, 0, 0)`):

```
http://localhost:8000/overlay/party-vitals/{session_id}
```

### OBS Studio Configuration
1. In OBS Studio, add a new **Browser Source** to your tabletop scene.
2. Set **URL** to `http://localhost:8000/overlay/party-vitals/{session_id}?position=bottom`.
3. Set **Width** to `1920` and **Height** to `1080`.
4. Check **Shutdown source when not visible** and **Refresh browser when scene becomes active**.
5. Ensure **Custom CSS** is blank (the server serves `background: transparent !important`).

### URL Configuration Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `position` | `string` | `bottom` | Layout docking: `bottom`, `top`, or `sidebar` (280px left rail) |
| `easing` | `string` | `cubic-bezier(0.25, 0.1, 0.25, 1.0)` | Viewport transition cubic-bezier easing curve |
| `duration` | `integer` | `300` | Smooth camera pan/zoom duration in milliseconds (< 300ms SLA) |
| `format` | `string` | `html` | Output format: `html` (OBS browser source) or `json` (REST data) |

---

## 2. Server-Side Zanzibar Secret Sanitization

The spectator overlay strictly enforces server-side SpiceDB Zanzibar permissions:
- **100% Secret Stripping**: All DM-only private notes (`dm_notes`), hidden traps, stealth monster tokens, and unrevealed monster HP numbers are stripped before rendering.
- **Party Member Isolation**: Only friendly player characters and active AI stand-ins are displayed on the stream vitals HUD.
- **Audience Safe**: Even if a malicious client inspects the OBS DOM or network traffic, no DM secrets or trap coordinates exist in the response payload.

---

## 3. Autonomous Cinematic Director Camera

The cinematic director automatically tracks live gameplay events:
1. **Turn Started (`TurnStarted`)**: When a combat round or turn cycles, the camera centers on the active token using smooth cubic-bezier easing within 300ms.
2. **Action Centers (`TokenMoved`)**: When a token traverses the grid, the camera follows the destination center `(to_x, to_y)` at a configured zoom level (1.5x - 2.0x).
3. **Hidden Movement Shielding**: Movements made by hidden monsters or invisible creatures are omitted from spectator feeds to prevent visual spoilers.

### WebSockets Integration

Connect to the dedicated spectator WebSocket feed (available at `ws://localhost:8000/ws/overlay/${sessionId}` or alias `ws://localhost:8000/overlay/ws/${sessionId}`):

```javascript
const ws = new WebSocket(`ws://localhost:8000/overlay/ws/${sessionId}`);

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  if (msg.type === "camera_target_updated") {
    console.log("Auto-Camera Target:", msg.camera.target_x, msg.camera.target_y, msg.camera.zoom);
  } else if (msg.type === "roll_animation") {
    console.log("Dice Roll Animation:", msg.roller_name, msg.dice_formula, msg.result);
  }
};
```

---

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
