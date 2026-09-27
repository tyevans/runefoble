# How-To: Modulate DM Live Vocal Audio & NPC Formant Presets

This guide explains how Dungeon Masters and voice actors can apply real-time DSP vocal transformations ("Ancient Dragon", "Goblin Skulker", "Celestial Spirit", "Robotic Construct") to outgoing audio streams with low processing latency (<50ms).

Governed by:
- **ADR-0002**: Event-Driven Watcher Gameplay Orchestration
- **ADR-0003**: UV Monorepo Workspace for Python BCs
- **ADR-0007**: Domain-Driven Design Architecture
- **ADR-0011**: eventsource-py Core Event Sourcing
- **PRD-0004**: Voice Streaming and DSP Pipeline
- **US-0020**: DM Voice Modulation & NPC Personas
- **TASK-0157**: DM Live Vocal Modulator and Real-Time NPC Formant DSP Engine

---

## 1. Architecture Overview

To eliminate vocal fatigue during marathon sessions, `services/voice_agent` provides a modular Digital Signal Processing (DSP) engine operating on 16-bit linear PCM audio buffers.

```
+--------------------------------------------------------------------------+
| Game Master / Stream Broadcaster Microphone                              |
+--------------------------------------------------------------------------+
       | (Raw PCM Audio Frames)
       v
+--------------------------------------------------------------------------+
| Voice Agent Modular DSP Pipeline (`voice_agent.dsp.StreamPipelineFilter`)|
|  1. Pitch Shift Processing (WebAudio dual-tap delay crossfade)           |
|  2. Formant Pole Resonances (Biquad peak/notch filters)                 |
|  3. Special FX Stacks (Ring modulation / Robotic carrier, Reverb space)  |
|  4. Low-Latency Execution Benchmarking (< 50ms per frame)                |
+--------------------------------------------------------------------------+
       |
       +---> Dispatched to WebRTC Voice Track & Tabletop Broadcast
       |
       v (Publishes `runefoble.voice.modulator.preset_applied.v1`)
+--------------------------------------------------------------------------+
| Redis Streams (`runefoble.events.voice`)                                 |
+--------------------------------------------------------------------------+
```

---

## 2. Available Creature Archetype Presets

Query the preset catalog via the frontdoor endpoint `GET /voice/presets`:

| Preset ID | Pitch Scale | Formant Shift | Resonance | Special FX |
|---|---|---|---|---|
| `ancient_dragon` | 0.65 (-5 semitones) | 0.70 (Sub-bass throat) | 0.80 | Wet room reverb (0.35) |
| `goblin_skulker` | 1.45 (+6 semitones) | 1.35 (Nasal resonance) | 0.60 | Dry bite / presence |
| `celestial_spirit`| 1.15 (+2 semitones) | 1.10 (Ethereal aura) | 0.40 | Shimmer reverb (0.55) |
| `robotic_construct`| 0.90 (-2 semitones) | 0.85 (Metallic hollow) | 0.75 | Ring modulation (50Hz) |

---

## 3. Applying Vocal Modulation via Frontdoor REST API

### Inspecting Presets
```bash
curl -X GET "https://runefoble.local/voice/presets" \
  -H "Authorization: Bearer <jwt-token>"
```

### Applying a Preset to an Active Session
```bash
curl -X POST "https://runefoble.local/voice/modulate" \
  -H "Authorization: Bearer <jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session-camp-01",
    "preset_id": "ancient_dragon",
    "filter_enabled": true
  }'
```

### Overriding DSP Parameters Dynamically
DMs can fine-tune pitch scale and formant shift directly while keeping a base archetype:
```bash
curl -X POST "https://runefoble.local/voice/modulate" \
  -H "Authorization: Bearer <jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session-camp-01",
    "preset_id": "goblin_skulker",
    "pitch_scale": 1.55,
    "formant_shift": 1.40,
    "filter_enabled": true
  }'
```

---

## 4. Processing Live PCM Audio Frames in Code

Use `StreamPipelineFilter` directly within real-time streaming handlers:

```python
from voice_agent.dsp import StreamPipelineFilter, get_preset

# Initialize filter with a creature archetype
pipeline = StreamPipelineFilter(preset=get_preset("ancient_dragon"))

# Transform incoming 16-bit 16kHz PCM audio bytes
processed_bytes, latency_ms = pipeline.process_frame(raw_pcm_bytes)

assert latency_ms < 50.0  # Guarantees sub-50ms processing
```

---

## 5. Domain CloudEvents Emitted

When vocal modulation presets are applied or toggled, the following CloudEvents are published to Redis Streams:
- `runefoble.voice.modulator.preset_applied.v1`: Contains `session_id`, `speaker_id`, `preset_id`, `pitch_scale`, `formant_shift`, `resonance`, and `fx_chain`.
- `runefoble.voice.modulator.filter_toggled.v1`: Emitted when bypass or toggle is changed with `enabled: bool`.

---

## 6. Using the `<runefoble-vocal-modulator>` Microfrontend

For one-touch control during live sessions, `services/voice_agent/ui` vendors `<runefoble-vocal-modulator>`:

```html
<runefoble-vocal-modulator
  session-id="session-camp-01"
  peer-id="dm_speaker"
></runefoble-vocal-modulator>
```

### Key Capabilities & Shortcuts
- **Instant Archetype Presets**: One-tap toggles for Ancient Dragon (`1`), Goblin Skulker (`2`), Celestial Spirit (`3`), and Robotic Construct (`4`).
- **Bypass Toggle**: Press `B` or tap the active status button to instantly toggle bypass and prevent in-character leakage.
- **Glowing Active LED**: High-contrast pulsing indicator clearly displays when modulation DSP is actively transforming outgoing audio.
- **Fine-Tuning Sliders**: Expand `<runefoble-vocal-sliders>` to manually calibrate pitch shift (±12 st), formant scale (0.5x–2.0x), resonance (0–4000 Hz), and octave offsets.
- **Emitted Custom Events**: Dispatches `vocal-modulate`, `preset-select`, and `vocal-param-change` events for seamless App Shell and WebRTC pipeline synchronization.

