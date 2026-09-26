---
id: '0064'
title: WebRTC Voice Room Signaling and Blackbox Test Suite Modular Decomposition
status: Proposed
created: 2026-09-26
dependencies: [TASK-0033]
governing_adrs: [ADR-0001, ADR-0002, ADR-0003]
target_release: 0.2.0
---

# TASK-0064: WebRTC Voice Room Signaling and Blackbox Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `gateway/api/src/gateway_api/webrtc_signaling.py` (383 lines, 76.6% of limit) and its integration test suite `tests/test_blackbox_webrtc_signaling.py` (350 lines, 70.0% of limit) into modular submodules (`signaling_manager.py`, `signaling_auth.py`, `signaling_handlers.py`) and focused test suites before Hard Invariant 6 (File length limit < 500 lines) is breached as WebRTC capabilities expand.

## Problem Statement
`gateway/api/src/gateway_api/webrtc_signaling.py` currently spans 383 lines and combines four distinct responsibilities:
1. Active WebSocket connection lifecycle, peer registry, and room broadcasting (`WebRTCSignalingManager`).
2. Authentication extraction from query parameters/headers and SpiceDB Zanzibar permission verification (`extract_signaling_auth`, `validate_voice_connection`).
3. Core WebRTC signaling event dispatching: SDP offer/answer exchange, ICE candidate routing, mute toggling, and DM moderation kicks (`voice_signaling_websocket_endpoint`).
4. Event coordination with the `VoiceRoomCoordinator` from `voice_agent`.

Similarly, `tests/test_blackbox_webrtc_signaling.py` (350 lines) tests connection handshakes, Zanzibar authorization failures, peer arrivals, offer/answer flows, ICE exchange, and DM kicks in a single monolithic test file.

As audio capabilities expand in upcoming milestones (whisper tracks, autonomous DM voice injection, recording, and spatial audio), these files will quickly exceed the 500-line ceiling.

## Proposed Decomposition
1. **Signaling Connection Manager (`gateway/api/src/gateway_api/signaling/manager.py`)**:
   - Manages active room WebSockets, peer lookups, kick callbacks, and JSON broadcasts (< 120 lines).
2. **Signaling Zanzibar Auth (`gateway/api/src/gateway_api/signaling/auth.py`)**:
   - Query param/header credential extraction and SpiceDB Zanzibar session/campaign permission checks (< 90 lines).
3. **Signaling Message Handlers (`gateway/api/src/gateway_api/signaling/handlers.py`)**:
   - Dispatchers for `webrtc_offer`, `webrtc_answer`, `webrtc_ice_candidate`, `webrtc_mute`, and `webrtc_kick` (< 140 lines).
4. **Endpoint Facade (`gateway/api/src/gateway_api/webrtc_signaling.py`)**:
   - Re-exports `WebRTCSignalingManager`, `signaling_manager`, and `voice_signaling_websocket_endpoint` for backward compatibility (< 80 lines).
5. **Test Suite Modularization (`tests/webrtc/` or split files)**:
   - `tests/test_blackbox_webrtc_auth.py`: Connection, credential extraction, and Zanzibar permission rejection (< 180 lines).
   - `tests/test_blackbox_webrtc_routing.py`: SDP offer/answer, ICE candidates, muting, and DM kick actions (< 220 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors internal signaling implementation without altering WebSocket wire protocols, message schemas, or external APIs.
- **Negotiable (N)**: Exact module names and boundaries within `gateway_api/signaling/` can be adjusted.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (< 500 lines) and improves maintainability of live WebRTC infrastructure.
- **Estimable (E)**: Standard Python module extraction and test suite partitioning.
- **Small (S)**: Scope strictly isolated to `gateway_api/` and `tests/test_blackbox_webrtc_signaling.py`; all resulting files < 220 lines.
- **Testable (T)**: Full test coverage verified with `uv run pytest tests/test_blackbox_webrtc*.py`.

## Acceptance Criteria
1. Re-exports in `webrtc_signaling.py` ensure 100% backward compatibility for all existing imports and routes.
2. All modified and newly created source files strictly under 250 lines.
3. Zero wire protocol changes: client WebSockets receive identical JSON event payloads.
4. 100% test pass rate across WebRTC test suites.
5. Conforms strictly to Hard Invariant 6 (< 500 lines per file).
