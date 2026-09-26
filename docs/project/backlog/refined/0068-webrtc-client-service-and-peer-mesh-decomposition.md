---
id: '0068'
title: WebRTC Client Voice Service and Peer Connection Mesh Modular Decomposition
status: Refined
created: 2026-09-26
dependencies:
- TASK-0033
governing_adrs:
- ADR-0002
- ADR-0004
- ADR-0009
- ADR-0013
target_release: 0.3.0
governing_prds:
- PRD-0004
governing_stories:
- US-0011
---

# TASK-0068: WebRTC Client Voice Service and Peer Connection Mesh Modular Decomposition

## Status
Refined

## Summary
Decompose `frontend/src/services/webrtc-voice.ts` (348 lines, 69.6% of limit) into modular TypeScript files (`webrtc-types.ts`, `webrtc-peer-mesh.ts`, and `webrtc-voice.ts`) to maintain clean separation of concerns and prevent breaching Hard Invariant 6 (File length limit < 500 lines) as real-time audio features expand.

## Problem Statement
`frontend/src/services/webrtc-voice.ts` currently spans 348 lines and bundles multiple distinct responsibilities:
1. Type declarations and protocol interfaces (`VoicePeer`, `SignalingMessage`, `WebRTCVoiceOptions`).
2. WebSocket connection management, auto-reconnect timers, credential parameter encoding, and message serialization.
3. Peer connection mesh management: RTCPeerConnection instantiation, remote media stream tracking, SDP offer/answer exchanges, ICE candidate buffering/forwarding, and cleanup on disconnect.
4. Remote audio DOM element creation, muting, volume control, and WebAudio pipeline bridging.
5. Voice activity detection and speaking level callbacks.

As upcoming voice features (spatial audio positioning, DM whisper channels, multi-codec negotiation, and network quality metrics) are added, this file will quickly approach and exceed the 500-line invariant.

## Governing Architecture & ADRs
- **ADR-0002: The Watcher Autonomous DM**: Supporting DM private voice whispers and voice routing.
- **ADR-0004: Lit Web Components and Storybook UI**: Client service consumption in Lit UI components.
- **ADR-0009: Continuous Backlog Refinement and Technical Debt Management**: Preemptive frontend modularization.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Voice service contract boundaries.

## Proposed Decomposition
1. **WebRTC Protocol Types & Interfaces (`frontend/src/services/webrtc-types.ts`)**:
   - `VoicePeer`, `SignalingMessage`, `WebRTCVoiceOptions`, and connection state enums (< 70 lines).
2. **Peer Connection Mesh Coordinator (`frontend/src/services/webrtc-peer-mesh.ts`)**:
   - `PeerConnectionMesh`: RTCPeerConnection map, remote MediaStreams, SDP creation/answer processing, ICE candidate routing, and remote audio DOM elements (< 160 lines).
3. **Voice Client Service Facade (`frontend/src/services/webrtc-voice.ts`)**:
   - `WebRTCVoiceService`: WebSocket signaling transport, incoming dispatching, speaking status emission, and `WebAudioPipeline` coordination (< 150 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors client-side WebRTC service modules without changing public service interfaces or the WebSocket wire protocol.
- **Negotiable (N)**: Split boundaries between mesh coordination and DOM audio element management can be tailored.
- **Valuable (V)**: Prevents Hard Invariant 6 violations (< 500 lines) and improves modularity of real-time client audio systems.
- **Estimable (E)**: Standard TypeScript class and interface extraction.
- **Small (S)**: Scope strictly isolated to `frontend/src/services/webrtc-voice.ts`; all resulting files < 170 lines.
- **Testable (T)**: Verified with `pnpm run build` in `frontend/` and `uv run pytest tests/test_blackbox_webrtc_signaling.py`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. Full backward compatibility preserved for existing imports in frontend components and Storybook stories.
2. All modified and newly created TypeScript source files strictly under 200 lines.
3. Zero TypeScript compiler errors via `pnpm run build`.
4. Conforms strictly to Hard Invariant 6 (< 500 lines per file).
5. Passes `uv run pytest tests/test_blackbox_webrtc_signaling.py`.
