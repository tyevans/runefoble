# How-To: Handle Neural Voice Duplex & Speech Interruption (Barge-In)

This guide explains how to integrate and manage zero-latency bidirectional voice duplex turn-taking, human speech interruption detection (< 80ms), acoustic echo cancellation, and soft 20ms audio crossfade cancellation in Runefoble.

Governed by:
- **ADR-0002**: Event-Driven Watcher Architecture & Voice Audio
- **ADR-0006**: Redis Streams Event Bus Architecture
- **PRD-0004**: Dynamic Vocal Audio Conditioning and DSP Filters
- **US-0060**: Zero-Latency Neural Voice Duplex & Speech Interruption Handling
- **TASK-0141**: Zero-Latency Neural Voice Duplex & Speech Interruption Handling
- **TASK-0168**: Neural Speech Barge-In and Soft Crossfade Audio Filter
- **TASK-0169**: Hardware Acoustic Echo Cancellation and ERLE Validation

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

Clients establish a duplex voice control and audio streaming connection to the Voice Agent service.

### Identity Contract (TASK-0530)

The Voice Agent verifies the Zitadel bearer token itself (ADR-0015 c). It does not trust an identity header from the gateway.

- **HTTP routes** take the token only from `Authorization: Bearer <jwt>`. A request with no token, a garbage token, or a token from another issuer returns `401` with `WWW-Authenticate: Bearer`. `X-User-Id` and `?user_id=` are ignored. After the token passes, each route checks one schema permission. The subject is the token subject, or the speaker that the request names. A denial returns `403`. A SpiceDB outage returns `503` with `{"error": "authorization_unavailable"}`. The full route table is in [Voice Agent Permissions](../reference/ports-and-endpoints.md#voice-agent-permissions-task-0558).
- **WebSocket routes** (`/api/v1/voice/duplex/ws/...`, `/api/v1/voice/stream/ws/...`) take the token only from the `runefoble.bearer.<jwt>` subprotocol. The client offers `runefoble.v1` and `runefoble.bearer.<jwt>`. The service accepts the handshake with `runefoble.v1`. A handshake with no valid token closes with code `1008` before accept. A token in the query string is refused.
- `GET /healthz` and `GET /ui/manifest` stay public.

```typescript
const token = accessToken; // Zitadel access token for the signed-in user
const sessionId = "session-campaign-12";
const speakerId = "spk-marcus";
const ws = new WebSocket(
  `wss://runefoble.local/api/v1/voice/duplex/ws/${sessionId}/${speakerId}?speaker_name=Marcus`,
  ["runefoble.v1", `runefoble.bearer.${token}`]
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

## 5. Reacting to a Barge-In

A barge-in reaches the client as frames on the duplex WebSocket. The `barge_in_detected` frame carries `cutoff_ms` and `remaining_text`. The `playback_canceled` frame follows it. No Redis Streams event is published for a barge-in.

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
- **Client frames**: The duplex socket sends the `barge_in_detected` and `webrtc_stream_mute` frames. No Redis Streams event is published for a barge-in.

### Diagnostic Evaluation Frontdoor API

The diagnostic endpoint evaluates synthetic or captured audio frames and returns onset metrics and attenuated PCM waveforms:

```bash
curl -X POST http://voice-agent.runefoble.svc.cluster.local:8005/api/v1/voice/filters/barge-in/evaluate \
  -H "Authorization: Bearer $TOKEN" \
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

---

## 8. Hardware Acoustic Echo Cancellation & ERLE Validation (TASK-0169)

To ensure tabletop players can converse through open room speakers without headphones, `voice_agent.aec` provides adaptive echo cancellation with > 35dB Echo Return Loss Enhancement (ERLE) and zero voice distortion:

### Architecture Components
- **`NLMSAECFilter` (`voice_agent.aec.nlms_filter`)**: Adaptive Normalized Least Mean Squares transversal filter computing loudspeaker room impulse responses and subtracting acoustic reflections.
- **`DoubleTalkDetector` (`voice_agent.aec.double_talk`)**: Finite state machine detecting simultaneous human speech (`DoubleTalkState.DOUBLE_TALK`) via Geigel ratio, freezing filter adaptation to eliminate weight divergence.
- **`ResidualEchoSuppressor` (`voice_agent.aec.double_talk`)**: Post-filter applying up to 28dB attenuation to residual echo during `FAR_END_ONLY` state while passing near-end speech transparently with 1.0 gain.
- **`AECPipeline` (`voice_agent.aec.pipeline`)**: High-performance coordinator running frame-by-frame cancellation, metric computation, and ERLE validation.
- **Response**: The benchmark endpoint returns the ERLE, the pass state, and the echo detection flag. No Redis Streams event is published.

### Diagnostic Benchmark Frontdoor API

The diagnostic endpoint evaluates paired loudspeaker and microphone PCM streams to benchmark ERLE:

```bash
curl -X POST http://voice-agent.runefoble.svc.cluster.local:8005/api/v1/voice/aec/benchmark \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session-campaign-12",
    "speaker_id": "spk-marcus",
    "reference_audio_base64": "<base64-pcm-speaker>",
    "microphone_audio_base64": "<base64-pcm-mic>",
    "filter_length": 512,
    "step_size": 0.25,
    "erle_target_db": 35.0
  }'
```

Response includes:
```json
{
  "session_id": "session-campaign-12",
  "speaker_id": "spk-marcus",
  "erle_db": 59.59,
  "erle_target_db": 35.0,
  "passed": true,
  "double_talk_detected": false,
  "echo_detected": true,
  "attenuation_applied": true,
  "cleaned_audio_base64": "...",
  "initial_rms": 4469.31,
  "residual_rms": 4.69,
  "status": "success",
  "diagnostics": {
    "filter_length": 512,
    "step_size": 0.25,
    "sample_rate": 16000
  }
}
```

## 9. Speech-to-Text Engine Selection & Failure Behaviour (TASK-0600)

The voice agent transcribes completed utterances with a configured speech engine. Production has no canned transcript. The engine is set through environment variables with the `RUNEFOBLE_VOICE_` prefix:

| Variable | Default | Meaning |
|---|---|---|
| `RUNEFOBLE_VOICE_STT_ENGINE` | `faster-whisper` | Speech engine. `faster-whisper` runs in the pod. `whisper-cpp` calls a whisper.cpp HTTP server (TASK-0833). |
| `RUNEFOBLE_VOICE_STT_BASE_URL` | unset | Base URL of the whisper.cpp server, for example `http://<host>:8080`. Required for `whisper-cpp`. Start-up fails without it. |
| `RUNEFOBLE_VOICE_STT_REQUEST_TIMEOUT_SECONDS` | `30` | Timeout for one `whisper-cpp` transcription request. |
| `RUNEFOBLE_VOICE_STT_MODEL_SIZE` | `tiny.en` | faster-whisper model name (for example `tiny.en`, `base.en`). |
| `RUNEFOBLE_VOICE_STT_DEVICE` | `cpu` | CTranslate2 device. |
| `RUNEFOBLE_VOICE_STT_COMPUTE_TYPE` | `int8` | CTranslate2 compute type. |
| `RUNEFOBLE_VOICE_STT_MODEL_DIR` | unset (Hugging Face default cache) | Directory that holds the model cache. The Helm chart mounts a volume here. |
| `RUNEFOBLE_VOICE_STT_DOWNLOAD_ENABLED` | `true` | When `true`, the model downloads on first use. When `false`, the model must already sit in `RUNEFOBLE_VOICE_STT_MODEL_DIR`. The Helm chart sets `false`. |

Local development downloads the model on first use. The Kind cluster has no internet access. Run `make voice-model-cache` to copy the model into the running voice-agent pod.

### whisper.cpp HTTP Engine (TASK-0833)

Set `RUNEFOBLE_VOICE_STT_ENGINE=whisper-cpp` and `RUNEFOBLE_VOICE_STT_BASE_URL` to the server base URL. The adapter does this for each completed utterance:

- It wraps the PCM audio as a mono 16-bit WAV file.
- It sends `POST {base_url}/inference` as multipart form data. The fields are `file` (the WAV), `response_format` (`json`), and `temperature` (`0.0`).
- It reads the `text` field of the JSON reply and removes the surrounding spaces.

A connection error, timeout, non-2xx reply, or reply without `text` returns `503` with `{"detail": {"error": "speech_engine_unavailable", "engine": "whisper-cpp", "message": "..."}}`. The adapter never returns substitute text.

`GET /healthz` calls `GET {base_url}/health`. The route returns `503` with `"status": "not_ready"` and `problems.stt` when the server does not answer with a 2xx status.

In Helm, set `services.voiceAgent.sttEngine: whisper-cpp` and `services.voiceAgent.sttBaseUrl`. The chart then renders no model cache volume. See `docs/reference/platform-services.md`.

### Failure Behaviour

When the engine fails to load a model or to infer text, the utterance is dropped and the caller receives an explicit error:

- `POST /api/v1/voice/stream/chunk` returns `503` with `{"detail": {"error": "speech_engine_unavailable", "engine": "faster-whisper", "message": "..."}}`.
- `WS /api/v1/voice/stream/ws` sends `{"error": "speech_engine_unavailable", "engine": "...", "message": "..."}` and keeps the socket open.
- A RIFF body with no `data` chunk, or shorter than the 44-byte header, returns `400` with `{"error": "audio_format_invalid", "message": "..."}` on the HTTP routes. The WebSocket sends the same body as a frame and keeps the socket open. The service never reads such bytes as raw PCM.
- The route returns the 503 and records no speech. No Redis Streams event is published for the failure.
- No `runefoble.events.watcher.player_spoke` is published, and The Watcher receives no transcript.

Check the active engine with `GET /healthz`. The response includes `"stt_engine": "faster-whisper"`.

With download disabled, `GET /healthz` returns `503` and `"status": "not_ready"` when the cache holds no model for `RUNEFOBLE_VOICE_STT_MODEL_SIZE`. The body names the failing engine in `problems.stt`.

Callers cannot supply a transcript. The chunk request and the WebSocket frame do not accept `mock_transcript`. The configured engine always decides the text.

### Transcribe Route Input (TASK-0602)

`POST /api/v1/voice/transcribe` accepts one of two inputs:

| Input | Source label | Behaviour |
|---|---|---|
| `audio_base64` | `audio` | The service decodes the base64 audio (WAV or raw PCM) and calls the STT port. The engine text becomes the player action. |
| `transcript` | `client_text` | The service uses the typed text as given. |

Rules:

- Send neither input, or a blank `transcript`, and the route returns `422`. No event is published.
- Send invalid base64 in `audio_base64`, and the route returns `422`. No event is published.
- Send both inputs, and the audio wins. The typed text is ignored.
- Audio that the engine transcribes to no words returns `200` with `transcript` set to `""`. No `runefoble.events.watcher.player_spoke` is published, and The Watcher receives nothing.
- An unavailable engine returns `503` with `error: speech_engine_unavailable`. The route never falls back to typed or canned text.

The response carries `source` so that callers can tell the two inputs apart.

### Test Setup

Blackbox tests inject a deterministic engine (`tests/helpers/fixture_transcriber.py`) into the composition root. Tests that need an unavailable engine set `RUNEFOBLE_VOICE_STT_MODEL_SIZE` to an unknown model name and `HF_HUB_OFFLINE=1`. See `tests/test_blackbox_voice_stt_engine.py` and `tests/test_blackbox_voice_transcribe_input.py`.

Tests for `whisper-cpp` run a loopback HTTP server (`tests/helpers/local_http_server.py`) as the whisper.cpp stand-in. See `tests/test_blackbox_voice_whisper_cpp.py`.

## 10. Text-to-Speech Engine and Synthesis Output (TASK-0601)

`POST /api/v1/voice/synthesize` renders the persona text with the configured speech synthesis engine. It then applies the requested DSP filters to that audio and returns the audio.

| Variable | Default | Meaning |
|---|---|---|
| `RUNEFOBLE_VOICE_TTS_ENGINE` | `espeak-ng` | Speech synthesis engine. `espeak-ng` is the only supported value. |
| `RUNEFOBLE_VOICE_TTS_BINARY` | `espeak-ng` | Path or name of the engine binary. The adapter runs `espeak-ng --stdout -v <voice> --stdin` and sends the text on stdin. |

The voice-agent image installs `espeak-ng`. The Dockerfile build argument `SYSTEM_PACKAGES` adds it. The service does not install packages at pod start.

### Output Contract

- The response carries a WAV file in `audio_base64`. `duration_ms` is computed from the sample count and `sample_rate_hz`.
- The response has no stream URL. `content_sha256` identifies the audio.
- The voiced text is the request `text`. `conditioned_text` is returned as metadata only.
- `POST /api/v1/voice/dsp/apply` filters supplied audio only. It returns `422` when `audio_base64` is missing.

### Failure Behaviour

When the engine cannot start, exits with an error, times out, or returns no audio, the route returns `503` with `{"detail": {"error": "speech_synthesis_unavailable", "engine": "espeak-ng", "message": "..."}}`. No tone or placeholder audio is returned. The health route reports `"tts_engine": "espeak-ng"`.

`GET /healthz` runs `espeak-ng --version`. A missing or failing binary returns `503` with `"status": "not_ready"` and `problems.tts`.

### Test Setup

Blackbox tests inject a deterministic fake (`tests/helpers/fixture_synthesizer.py`) through the `fake_speech_synthesizer` fixture. The fake renders 40 ms of tone per character, so audio length follows the text. Failure tests set `RUNEFOBLE_VOICE_TTS_BINARY` to a missing path or to a script that exits with an error. See `tests/test_blackbox_voice_tts.py`.

## 11. Playback and Room State Ownership (TASK-0577)

The voice service owns the state of each voice room. The state includes the peers, the active TTS playback, and the stream quality of each peer. The state is stored in the room aggregate in the event store. No replica keeps this state in memory. A replica reads the state through the public frontdoor.

### Playback Lifecycle

1. `POST /api/v1/voice/duplex/playback/start` or the WebSocket frame `playback_start` starts a playback. The service saves `VoicePlaybackStarted`.
2. `GET /api/v1/voice/duplex/status/{session_id}` returns `playback_active`. It reads the saved state.
3. Player speech that the barge-in detector confirms stops the playback. The service saves `VoicePlaybackAttenuated` and `VoicePlaybackStopped`. Then it publishes `voice.speech.interrupted`.

The playback events are saved only. They are not published. Use `voice.speech.interrupted` to react to a barge-in.

### Failure Behaviour

If the event store cannot load or save the room, the route answers `503`. The service does not publish an event for a command that failed to save.

### Test Setup

Blackbox tests start a playback through the HTTP route, build a new coordinator to model a restart, and then read the status through the same route. See `tests/test_blackbox_voice_duplex_state.py`.

### Graceful Restart Keeps Room Seats

When voice_agent stops gracefully (SIGTERM or a rolling deploy), it closes each signaling socket with code `1012` (service restart). A peer that closes with `1012` keeps its seat. The service does not save `VoicePeerLeft` and does not broadcast `webrtc_peer_left` for it. The room aggregate in the event store still lists the peer after the restart.

A client reconnects to `/ws/voice/{session_id}` with the same `peer_id`. The service then sends `webrtc_joined` with the room's peers. Browsers cannot send close code `1012`, so only the server sends it. A crash (SIGKILL) runs no shutdown code. A peer that the crash leaves behind stays in the room until it leaves or is kicked.

Blackbox test: `tests/test_blackbox_voice_room_restart.py`.

### Peer Telemetry Is Not Stored

Peer audio telemetry (`webrtc_telemetry`) is not domain state. The service does not save it to the event store. The service keeps the latest sample for each peer in a bounded, in-process view. A restart clears the view, and each replica sees only the samples that reach it. Each sample also feeds OpenTelemetry instruments (`voice.telemetry.updates`, `voice.telemetry.latency`). The platform does not yet configure a meter provider, so these instruments record nothing until one is set up.
