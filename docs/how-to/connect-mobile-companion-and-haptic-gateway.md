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

The mobile companion component is vendored in `@runefoble/voice-agent-ui` and advertised via `/ui/manifest`:

```html
<runefoble-mobile-companion
  sessionId="session-101"
  userId="marcus"
  channelName="Party Voice (Cellular Opus)"
  .connected=${true}
  audioTier="mobile_optimized"
  .sampleRate=${16000}
  .bitrateKbps=${16}
  .bufferHealthMs=${45}
  .privacyBlur=${true}
  .packetLoss=${0.02}
  .bandwidthKbps=${120}
></runefoble-mobile-companion>
```

### Component Capabilities
- **Tactile Push-to-Talk**: Large thumb-friendly button triggering `ptt-start` and `ptt-end` events with light 15ms haptic confirmation.
- **Diegetic Secret Whisper Overlay**: Subtle parchment modal with privacy blur (`filter: blur(...)`) to prevent shoulder surfing, acoustic chime via WebAudio `AudioContext`, and instant reveal/conceal toggle.
- **Audio Buffer Monitor**: Displays real-time audio buffer health (target 45ms) and cellular stream tier indicators (`mobile_optimized`, `cellular_constrained`, `ultra_low`).
- **WebSocket Protocol Dispatcher**: Direct client-side connection support via `.connectWebSocket(url)` and message handler for `haptic_vibration`, `haptic_ping`, and `audio_profile_adapted` frames.
- **Custom Event Contracts**: Dispatches `haptic-pulse`, `whisper-received`, `whisper-dismissed`, `whisper-blur-toggled`, and `connection-changed`.

---

## 5. Decomposed Sub-Components

Per ADR-0004 and Hard Invariant 6, the mobile companion is decomposed into focused subcomponents under `@runefoble/voice-agent-ui`:

1. **Audio Stream Controller (`<audio-stream-controller>`)**:
   - Manages WebRTC Opus mono stream indicators, cellular bitrate selection (12, 16, 24 kbps), audio buffer health bars, and stream muting.
   - Emits: `bitrate-change`, `mute-toggle`.

2. **Haptic Ping Panel (`<haptic-ping-panel>`)**:
   - Handles secret DM whisper cards, privacy blur reveal/conceal toggling, acoustic chime synthesis (`AudioContext`), combat turn alert banners, and Web Vibration API feedback.
   - Emits: `haptic-pulse`, `whisper-received`, `whisper-dismissed`, `whisper-blur-toggled`, `turn-alert-dismissed`.

3. **Connection Status Badge (`<connection-status-badge>`)**:
   - Renders online/offline badges, cellular tier tags, live haptic pulse animations, round-trip latency readouts, and reconnection trigger buttons.
   - Emits: `reconnect`.

---

## 6. WebRTC RTCP Quality Monitoring & Adaptive Bitrate Diagnostics (TASK-0166)

The voice agent automatically scales individual WebRTC stream bitrates down to 16kHz mono Opus (<50 kbps) when cellular packet loss occurs:

### Reporting RTCP Telemetry via HTTP

Clients submit standard RTCP receiver reports to `/voice/streams/{session_id}/report`:

```bash
curl -X POST "http://localhost:8005/voice/streams/session-101/report" \
  -H "Content-Type: application/json" \
  -d '{
    "peer_id": "peer_marcus",
    "packet_loss": 0.08,
    "rtt_ms": 120.0,
    "jitter_ms": 14.5
  }'
```

- When packet loss > 5% or RTT > 250ms is detected, `VoiceStreamQualityDegradedEvent` is emitted.
- The `AdaptiveBitrateRegulator` steps transmission down to 12 kbps (`cellular_constrained` mode) or 8 kbps (`ultra_low` mode) within 200ms.
- A `VoiceStreamCodecAdaptedEvent` is published to Redis Streams.

### Querying Stream Diagnostics

Inspect the active stream quality, bitrate, and codec mode via `/voice/streams/{session_id}/quality`:

```bash
curl "http://localhost:8005/voice/streams/session-101/quality?peer_id=peer_marcus"
```

Response:
```json
{
  "session_id": "session-101",
  "peer_id": "peer_marcus",
  "bitrate_kbps": 12,
  "packet_loss": 0.08,
  "codec_mode": "cellular_constrained",
  "sample_rate": 16000,
  "channels": 1,
  "complexity": 4,
  "fec_enabled": true,
  "dtx_enabled": true,
  "rtt_ms": 120.0,
  "jitter_ms": 14.5,
  "is_degraded": true,
  "severity": "degraded"
}
```



