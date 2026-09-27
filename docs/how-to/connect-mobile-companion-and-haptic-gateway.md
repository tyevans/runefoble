# How-To: Connect Mobile Companion WebRTC Audio & Haptic Ping Gateway

This guide explains how to connect smartphone and mobile companion clients to the low-bandwidth WebRTC audio and haptic vibration gateway in Runefoble (`/ws/mobile-companion/{session_id}`).

Governed by:
- **ADR-0002**: Event-Driven Watcher Architecture & Voice Audio
- **ADR-0005**: Kubernetes-First Infrastructure & Ingress Routing
- **ADR-0013**: Microfrontend Architecture and Component Vendoring
- **PRD-0004**: Dynamic Vocal Audio Conditioning and DSP Filters
- **US-0059**: Spatial Companion Mobile WebRTC Audio & Haptic Secret Pings

---

## 1. Connecting via WebSocket Frontdoor

Mobile devices connect to the API Gateway at `/ws/mobile-companion/{session_id}`. SpiceDB Zanzibar permissions are strictly verified on connection.

```typescript
const sessionId = "session-adventure-101";
const userId = "marcus";
const ws = new WebSocket(
  `wss://runefoble.local/ws/mobile-companion/${sessionId}?user_id=${userId}&peer_id=peer_${userId}`
);

ws.onopen = () => {
  console.log("Connected to spatial mobile companion gateway");
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  switch (data.type) {
    case "mobile_companion_connected":
      handleInitialProfile(data.audio_profile);
      break;
    case "haptic_ping":
      handleHapticPing(data);
      break;
    case "audio_profile_adapted":
      handleProfileAdapted(data);
      break;
  }
};
```

---

## 2. Low-Bandwidth Adaptive Opus Profiles

The mobile companion stream runs a voice-optimized 16kHz mono Opus profile with Forward Error Correction (FEC) and Discontinuous Transmission (DTX) enabled to conserve battery and survive high-packet-loss cellular connections.

| Profile Tier | Sample Rate | Channels | Bitrate | Trigger Condition |
|---|---|---|---|---|
| `mobile_optimized` | 16 kHz | 1 (mono) | 16 kbps | Nominal cellular connection |
| `cellular_constrained` | 16 kHz | 1 (mono) | 12 kbps | Packet loss ≥ 5% or Bandwidth < 50 kbps |
| `ultra_low` | 16 kHz | 1 (mono) | 8 kbps | Packet loss ≥ 15% or Bandwidth < 25 kbps |

### Reporting Telemetry for Automatic Adaptation

Mobile companions report real-time packet loss and bandwidth to trigger gateway audio adaptation without dropping the connection:

```typescript
ws.send(JSON.stringify({
  type: "mobile_telemetry",
  packet_loss: 0.08,        // 8% loss
  bandwidth_kbps: 35.0,     // Constrained cellular
  latency_ms: 140.0
}));
```

The gateway immediately responds with an `audio_profile_adapted` frame and publishes `MobileAudioProfileAdapted` over the Redis event bus.

---

## 3. Haptic Vibration Patterns & Diegetic Lockscreen Whispers

When The Watcher or DM dispatches a secret clue or prompt, the mobile device triggers tactile feedback via the Web Vibration API:

```typescript
function handleHapticPing(frame) {
  const { alert_type, vibration_pattern, whisper, notification } = frame;

  // 1. Physical haptic vibration
  if ("vibrate" in navigator && vibration_pattern) {
    navigator.vibrate(vibration_pattern);
  }

  // 2. Lockscreen notification
  if (notification && Notification.permission === "granted") {
    new Notification(notification.title, {
      body: notification.body,
      tag: alert_type,
      vibrate: vibration_pattern,
      silent: false
    });
  }
}
```

### Standard Vibration Protocols

- **Secret DM Whisper**: Triple pulse `[200, 100, 200]` (200ms on, 100ms off, 200ms on). Delivered privately to the target player's device without alerting other party members.
- **Combat Turn Alert**: Double pulse `[300, 150, 300]` prompting the player for their initiative turn.
- **Critical Alert**: `[100, 50, 100, 50, 200]`.

---

## 4. Using the Lit Microfrontend (`<runefoble-mobile-companion>`)

The mobile companion component is vendored in `@runefoble/voice-agent-ui`:

```html
<runefoble-mobile-companion
  sessionId="session-101"
  userId="marcus"
  .connected=${true}
  audioTier="mobile_optimized"
  .sampleRate=${16000}
  .bitrateKbps=${16}
  .packetLoss=${0.02}
  .bandwidthKbps=${120}
></runefoble-mobile-companion>
```
