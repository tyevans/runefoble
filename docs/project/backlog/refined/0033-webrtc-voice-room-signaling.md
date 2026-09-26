---
id: '0033'
title: Live WebRTC Bidirectional Voice Room Signaling & WebAudio Pipeline
status: Refined
created: 2026-09-25
dependencies:
- TASK-0010
- TASK-0021
governing_adrs:
- ADR-0002
- ADR-0006
- ADR-0007
target_release: 0.2.0
---
# TASK-0033: Live WebRTC Bidirectional Voice Room Signaling & WebAudio Pipeline

## Status
Refined

## Summary
Implement live WebRTC bidirectional voice room signaling and session audio peer management in `services/voice_agent` and `gateway/api`. Users in an active collaborative tabletop session can join an ephemeral voice mesh/SFU room, negotiate SDP offers/answers and ICE candidates via WebSockets, and exchange low-latency bidirectional voice streams conditioned through the DSP pipeline (`TASK-0021`).

## Problem Statement & Architectural Context
Milestone 2 (Live Collaborative Alpha) requires live bidirectional voice communication so players and the Game Master can converse in real time. Spoken commands must flow seamlessly into speech-to-intent analysis ("Speak and the board obeys"), while character voices are conditioned dynamically based on game state (e.g. drunkenness, underwater, ethereal filters). While the audio DSP filter chain and TTS/transcribe endpoints are implemented, the real-time WebRTC signaling protocol that establishes peer-to-peer or peer-to-SFU connections across browsers and servers is needed.

## Governing Documents
- **ADRs**:
  - `ADR-0002`: Event-Driven Watcher Gameplay Orchestration
  - `ADR-0006`: Redis Streams Event Streaming
  - `ADR-0007`: Domain-Driven Design Architecture
- **Roadmap**: Milestone 2: Live Collaborative Alpha (Live WebRTC bidirectional voice room with WebAudio processing)
- **PRDs**: `PRD-0004` (Dynamic Vocal Audio Conditioning and DSP Filters), `PRD-0005` (Realtime WebSocket Board Sync)
- **User Stories**: `US-0004`, `US-0011`

## Scope of Work
1. **Domain Events (`libs/runefoble_events/src/runefoble_events/voice.py`)**:
   - `VoicePeerJoined`: `session_id`, `peer_id`, `user_id`, `role`, `joined_at`.
   - `VoicePeerLeft`: `session_id`, `peer_id`, `reason`.
   - `VoicePeerMuteToggled`: `session_id`, `peer_id`, `is_muted`.
   - Registered under `runefoble.events.voice.*` and re-exported.
2. **WebRTC Signaling Gateway (`gateway/api/src/gateway_api/webrtc_signaling.py` & WebSocket route)**:
   - Handle WebSocket messages for WebRTC signaling:
     - `webrtc_join`: Join room for a session.
     - `webrtc_offer`: Forward SDP offer to target peer or audio mixer.
     - `webrtc_answer`: Return SDP answer from peer.
     - `webrtc_ice_candidate`: Relay trickle ICE candidates.
     - `webrtc_leave`: Gracefully terminate audio connection.
   - Enforce room session membership and authentication token validation.
3. **Voice Room Coordinator (`services/voice_agent/src/voice_agent/room.py`)**:
   - Track active audio rooms, peer lists, latency telemetry, and speaker audio levels.
   - Frontdoor HTTP endpoint `GET /api/v1/voice/rooms/{session_id}` returning active room participants and speaking status.
   - Frontdoor HTTP endpoint `POST /api/v1/voice/rooms/{session_id}/kick` for DM moderation.
4. **WebAudio Browser Adapter (`frontend/src/services/webrtc-voice.ts`)**:
   - Client service managing `RTCPeerConnection`, `navigator.mediaDevices.getUserMedia`, and WebAudio `AudioContext`.
   - Connects audio output to DSP filter graph when character conditions apply.

## Definition of Done (Hard Invariant 7: Blackbox TDD Frontdoor Setup)
1. **Frontdoor Blackbox Verification**:
   - Tests connect to public WebSocket `/ws/voice/{session_id}` and HTTP `/api/v1/voice/rooms/{session_id}` endpoints.
   - End-to-end signaling exchange test verifies `join` -> `offer` -> `answer` -> `ice_candidate` message exchange between multiple simulated peer clients.
2. **Event & State Projections**:
   - Verifies `VoicePeerJoined` and `VoicePeerLeft` events published to `runefoble.events.session` upon peer connection and disconnection.
   - Querying `GET /api/v1/voice/rooms/{session_id}` reflects the exact list of connected peers.
3. **Mute & Moderation Controls**:
   - Tested through frontdoor WebSocket signals and HTTP moderation endpoints.
4. **Code Quality & Invariants**:
   - All files < 500 lines (Hard Invariant 6).
   - 100% pass on `uv run pytest` and clean `uv run ruff check .`.
   - Storybook audio indicator component verified in `frontend/src/stories/`.
