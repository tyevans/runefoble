# How-To: Handle Neural Voice Duplex & Speech Interruption (Barge-In)

This guide explains how to integrate and manage zero-latency bidirectional voice duplex turn-taking, human speech interruption detection (< 80ms), acoustic echo cancellation, and soft 20ms audio crossfade cancellation in Runefoble.

Governed by:
- **ADR-0002**: Event-Driven Watcher Architecture & Voice Audio
- **ADR-0006**: Redis Streams Event Bus Architecture
- **PRD-0004**: Dynamic Vocal Audio Conditioning and DSP Filters
- **US-0060**: Zero-Latency Neural Voice Duplex & Speech Interruption Handling
- **TASK-0141**: Zero-Latency Neural Voice Duplex & Speech Interruption Handling
- **TASK-0168**: Neural Speech Barge-In and Soft Crossfade Audio Filter

---

## 1. Architecture Overview

When The Watcher AI DM delivers narration or NPC dialogue over WebRTC audio, tabletop players must be able to interject immediate reaction spells (e.g. *"I cast Shield!"*) without waiting for the audio buffer to finish.

```
+--------------------------------------------------------------------------+
| Tabletop Client / Browser Microphone                                     |
+--------------------------------------------------------------------------+
       | (PCM audio frames)                               ^ (Mute & Cancel)
       v                                                  |
+--------------------------------------------------------------------------+
| Voice Agent Duplex Pipeline (/api/v1/voice/duplex/ws/{session_id})      |
|  1. Acoustic Echo Cancellation (AEC) -> Filter loudspeaker bleed        |
|  2. Neural VAD Barge-In Analyzer     -> Detect speech onset in < 80ms    |
|  3. Interruption Coordinator         -> Soft 20ms crossfade to silence   |
|  4. Cancellation Token Dispatch      -> Halt active TTS playback stream  |
+--------------------------------------------------------------------------+
       |
       v (Publish voice.speech.interrupted domain event)
+--------------------------------------------------------------------------+
| Redis Streams (`runefoble.events.voice`, `runefoble.events.session`)     |
+--------------------------------------------------------------------------+
```

---

## 2. Connecting via WebSocket Frontdoor

Clients establish a duplex voice control and audio streaming connection to the Voice Agent service:

```typescript
const sessionId = "session-campaign-12";
const speakerId = "spk-marcus";
const ws = new WebSocket(
  `wss://runefoble.local/api/v1/voice/duplex/ws/${sessionId}/${speakerId}?speaker_name=Marcus`
);

ws.onopen = () => {
  console.log("Connected to voice duplex channel");
};

ws.onmessage = (event) => {
  const frame = JSON.parse(event.data);
  switch (frame.type) {
    case "voice_duplex_connected":
      console.log("Duplex session established:", frame.session_id);
      break;
    case "barge_in_detected":
      console.warn(`Speech interrupted within ${frame.latency_ms}ms at position ${frame.cutoff_ms}ms`);
      break;
    case "webrtc_stream_mute":
      // Immediately mute the remote TTS playback track in WebRTC
      muteRemoteTrack(frame.stream_id);
      break;
    case "playback_canceled":
      console.log("Unvoiced narration tail:", frame.remaining_narration_text);
      break;
  }
};
```

---

## 3. Streaming Microphone Audio & Barge-In Detection

Microphone frames are streamed as binary 16-bit 16kHz mono PCM frames (or base64 encoded JSON messages):

```typescript
function sendMicrophoneAudioFrame(pcmBytes: Uint8Array) {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(pcmBytes);
  }
}
```

When human speech energy is detected for >= 60ms, the `BargeInDetector` signals an interruption within <= 80ms of onset, halting active TTS playback and notifying the client.

---

## 4. Acoustic Echo Cancellation (AEC)

To prevent the AI DM's own voice from echoing into open desktop microphones and causing false-positive barge-in triggers, clients or audio pipelines feed speaker reference audio frames:

```typescript
function registerSpeakerAudio(speakerPcmBytes: Uint8Array) {
  ws.send(JSON.stringify({
    type: "speaker_audio",
    audio_data: btoa(String.fromCharCode(...speakerPcmBytes))
  }));
}
```

The adaptive Normalized LMS echo canceller subtracts the speaker echo from the microphone buffer. If the microphone signal contains only speaker bleed, the frame is marked as `echo_suppressed` with zero false barge-in triggers.

---

## 5. Subscribing to `voice.speech.interrupted` Domain Events

The Watcher and session services subscribe to Redis Streams (`runefoble.events.voice` and `runefoble.events.session`) to save conversational state and listen to the interjecting player:

```python
from runefoble_events.events import VoiceSpeechInterrupted
from runefoble_platform.redis_bus import RedisConsumerGroup


async def handle_voice_events(consumer: RedisConsumerGroup):
    messages = await consumer.read_group(
        stream="runefoble.events.voice",
        group_name="watcher_speech_duplex",
        consumer_name="watcher_worker_1",
    )
    for msg_id, event in messages:
        if isinstance(event, VoiceSpeechInterrupted):
            print(f"Narrative paused at {event.cutoff_position_ms}ms by {event.speaker_name}")
            print(f"Unspoken remaining text: {event.remaining_narration_text}")
            await consumer.ack("runefoble.events.voice", "watcher_speech_duplex", msg_id)
```

---

## 6. Voice Duplex Controls & Real-Time Barge-In Visualizer Microfrontend

The `<runefoble-voice-duplex-controls>` Lit Web Component (TASK-0149) provides real-time visual feedback for conversational speech barge-in, active audio level metering, soft 20ms crossfade indicators, and duplex VAD calibration sliders.

### Component Usage

```html
<runefoble-voice-duplex-controls
  sessionId="session-campaign-12"
  speakerId="spk-marcus"
  speakerName="Marcus"
  .isConnected=${true}
  .vadSensitivity=${75}
  .duckingGainDb=${-12}
  .aecEnabled=${true}
></runefoble-voice-duplex-controls>
```

### Event Contracts

- `duplex-interrupted`: Dispatched when human speech onset interrupts active AI playback (detail: `{ speakerId, latencyMs, remainingText }`).
- `vad-sensitivity-change`: Dispatched when interruption sensitivity slider is adjusted (detail: `{ sensitivity }`).
- `ducking-gain-change`: Dispatched when acoustic ducking gain slider is modified (detail: `{ gainDb }`).
- `aec-toggle`: Dispatched when acoustic echo cancellation is toggled or retargeted (detail: `{ enabled, suppressionDb }`).

### Microfrontend Manifest Registration

The component is vendored inside `services/voice_agent/ui/` and advertised via the public HTTP endpoint `GET /ui/manifest`:

```bash
curl -s http://voice-agent.runefoble.svc.cluster.local:8005/ui/manifest | jq .components
# Output includes: "runefoble-voice-duplex-controls"
```

---

## 7. Neural Speech Barge-In Filter & Cosine Soft Crossfading (TASK-0168)

To eliminate harsh audio clipping and delayed conversational cutoffs, `voice_agent.dsp` provides sub-40ms onset detection coupled with a 20ms raised-cosine crossfade:

### Architecture Components
- **`BargeInOnsetFilter` (`voice_agent.dsp.barge_in_filter`)**: Audio ring-buffer evaluator continuously analyzing 10ms PCM frames for energy and zero-crossing rates, triggering barge-in within `< 40ms` of speech onset.
- **`CosineCrossfadeAttenuator` (`voice_agent.dsp.cosine_crossfade`)**: Smooth raised-cosine attenuation filter ($0.5 \times (1 + \cos(\pi \times (i+1)/N))$) damping outgoing TTS audio samples to zero amplitude across 20ms without pop artifacts.
- **CloudEvents**: Automatically publishes `runefoble.events.voice.barge_in_detected` and `runefoble.events.voice.tts_stream_attenuated` over Redis Streams.

### Diagnostic Evaluation Frontdoor API

The diagnostic endpoint evaluates synthetic or captured audio frames and returns onset metrics and attenuated PCM waveforms:

```bash
curl -X POST http://voice-agent.runefoble.svc.cluster.local:8005/voice/filters/barge-in/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session-campaign-12",
    "speaker_id": "spk-marcus",
    "speaker_name": "Marcus",
    "audio_base64": "<base64-pcm-speech>",
    "fade_duration_ms": 20.0,
    "energy_threshold": 350.0
  }'
```

Response includes:
```json
{
  "session_id": "session-campaign-12",
  "speaker_id": "spk-marcus",
  "barge_in_detected": true,
  "onset_latency_ms": 20.0,
  "confidence": 0.85,
  "rms_energy": 6363.9,
  "attenuation_applied": true,
  "fade_duration_ms": 20.0,
  "attenuated_audio_base64": "...",
  "peak_tail_amplitude": 0,
  "halt_latency_ms": 40.0,
  "status": "success"
}
```


