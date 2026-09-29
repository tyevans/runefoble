# PRD-0004: Dynamic Vocal Audio Conditioning and DSP Filters

## Status
Accepted

## Purpose
Voice immersion is paramount in collaborative tabletop roleplaying. When characters are afflicted by magical curses, excessive tavern drinking, fear, or environmental immersion (e.g. underwater, cathedral echo), their audio speech should organically reflect their state without breaking session flow. The `voice_agent` service will provide DSP audio filtering and speech cadence transformation for synthesized AI personas and streamed audio.

## Personas & User Needs
- **Sarah (Absent Player)**: When absent and penalized with "drunk" or "foolishness", her character's AI stand-in speaks with pitch flutters, slight hiccup insertions, and slurred phrasing.
- **Marcus (Adventurer)**: When afflicted by fear or underwater breathing, voice playback applies environmental DSP reverb/muffling.
- **Evelyn (Human DM)**: Auditory cues instantly signal to the whole table what status effects are active on any speaking character.

## Checkable Outcomes
1. The `voice_agent` service provides real-time DSP audio transforms: whisper (reduced dynamic range, high-pass shimmer), underwater (muffled low-pass, sub-bass resonance), ethereal (ghostly echo modulation, delay tail), and drunk (slurred formant modulation, pitch sway).
2. The `POST /api/v1/voice/dsp/apply` endpoint applies filter chains to raw audio streams or generates conditioned synthetic carriers under 50ms latency.
3. The `POST /api/v1/voice/tts` endpoint synthesizes persona audio streams applying active affliction filters, returning audio payloads, duration, and DSP metadata.
4. Each DSP conditioning cycle dispatches `VoiceAudioConditioned` CloudEvents-compliant domain events to Redis Streams.
5. Blackbox TDD test suite verifies filter presets, execution latency benchmarks (<50ms), and event dispatch via public frontdoors.

## Linked User Stories
- [`US-0011: Real-Time Dynamic Voice Filters for Afflicted Characters`](../../user_stories/accepted/us-0011-dynamic-voice-filters-for-afflicted-characters.md)
- [`US-0020: DM Vocal Modulator with Real-Time NPC Formant Filtering`](../../user_stories/accepted/us-0020-dm-vocal-modulator-with-realtime-npc-filtering.md)

## Implementing Backlog Tasks
- [`TASK-0005: Model Context Protocol (MCP) RPG Tools Expansion`](../../backlog/complete/0005-fastmcp-rpg-tools-expansion.md)
- [`TASK-0021: Real-Time Dynamic DSP Audio Conditioning Pipeline`](../../backlog/complete/0021-voice-dsp-conditioning-pipeline.md)
- [`TASK-0033: Live WebRTC Bidirectional Voice Room Signaling & WebAudio Pipeline`](../../backlog/complete/0033-webrtc-voice-room-signaling.md)
- [`TASK-0064: WebRTC Voice Room Signaling and Blackbox Test Suite Modular Decomposition`](../../backlog/complete/0064-webrtc-voice-signaling-and-test-suite-decomposition.md)
- [`TASK-0065: Voice Agent DSP Pipeline, Audio Routing, and Room Coordinator Modular Decomposition`](../../backlog/complete/0065-voice-agent-dsp-pipeline-and-router-decomposition.md)
- [`TASK-0068: WebRTC Client Voice Service and Peer Connection Mesh Modular Decomposition`](../../backlog/complete/0068-webrtc-client-service-and-peer-mesh-decomposition.md)
- [`TASK-0083: Streaming Whisper Audio Transcription Test Suite Modular Decomposition`](../../backlog/complete/0083-streaming-whisper-test-suite-modular-decomposition.md)
- [`TASK-0157: DM Live Vocal Modulator & Real-Time NPC Formant DSP Engine`](../../backlog/complete/0157-dm-vocal-modulator-formant-dsp-engine.md)
- [`TASK-0160: DM Vocal Modulator Controls & Preset Selector Microfrontend`](../../backlog/complete/0160-dm-vocal-modulator-controls-microfrontend.md)
- [`TASK-0480: Gateway Voice DSP and Vocal Modulator API Routing & Zanzibar Proxy`](../../backlog/proposed/0480-gateway-voice-dsp-and-vocal-modulator-api-proxy.md)
- [`TASK-0481: App Shell DM Vocal Modulator Integration & Live Session Preset Synchronization`](../../backlog/proposed/0481-app-shell-dm-vocal-modulator-integration-and-preset-sync.md)
- [`TASK-0482: WebAudio Client-Side Formant and Pitch Shifting DSP Node Chain`](../../backlog/proposed/0482-webaudio-client-formant-and-pitch-shifting-dsp-nodes.md)
- [`TASK-0483: DM Vocal Modulation and Voice DSP Frontdoor Blackbox Test Suite`](../../backlog/proposed/0483-voice-dsp-and-vocal-modulator-blackbox-test-suite.md)
