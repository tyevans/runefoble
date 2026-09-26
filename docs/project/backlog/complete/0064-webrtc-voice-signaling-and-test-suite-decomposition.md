---
id: '0064'
title: WebRTC Voice Room Signaling and Blackbox Test Suite Modular Decomposition
status: Complete
created: 2026-09-26
dependencies:
- TASK-0033
governing_adrs:
- ADR-0001
- ADR-0002
- ADR-0003
- ADR-0007
- ADR-0009
target_release: 0.2.0
pr_url: https://github.com/tyevans/runefoble/pull/78
governing_prds:
- PRD-0004
governing_stories:
- US-0011
---
# TASK-0064: WebRTC Voice Room Signaling and Blackbox Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `gateway/api/src/gateway_api/webrtc_signaling.py` (382 lines, 76.4% of limit) and its integration test suite `tests/test_blackbox_webrtc_signaling.py` (350 lines, 70.0% of limit) into modular submodules (`signaling_manager.py`, `signaling_auth.py`, `signaling_handlers.py`) and focused test suites before Hard Invariant 6 (File length limit < 500 lines) is breached as WebRTC capabilities expand.

## Problem Statement
`gateway/api/src/gateway_api/webrtc_signaling.py` currently spans 382 lines and combines four distinct responsibilities:
1. Active WebSocket connection lifecycle, peer registry, and room broadcasting (`WebRTCSignalingManager`).
2. Authentication extraction from query parameters/headers and SpiceDB Zanzibar permission verification (`extract_signaling_auth`, `validate_voice_connection`).
3. Core WebRTC signaling event dispatching: SDP offer/answer exchange, ICE candidate routing, mute toggling, and DM moderation kicks (`voice_signaling_websocket_endpoint`).
4. Event coordination with the `VoiceRoomCoordinator` from `voice_agent`.

Similarly, `tests/test_blackbox_webrtc_signaling.py` (350 lines) tests connection handshakes, Zanzibar authorization failures, peer arrivals, offer/answer flows, ICE exchange, and DM kicks in a single monolithic test file.

As audio capabilities expand in upcoming milestones (whisper tracks, autonomous DM voice injection, recording, and spatial audio), these files will quickly exceed the 500-line ceiling.

## Governing Architecture & ADRs
- **ADR-0001**: SpiceDB Zanzibar Object Authorization.
- **ADR-0002**: The Watcher Autonomous DM.
- **ADR-0003**: UV Monorepo Workspace for Python Bounded Contexts.
- **ADR-0007**: Real-Time Voice and Board Synchronization.
- **ADR-0009**: Continuous Backlog Refinement and Technical Debt Management.

## Proposed Decomposition
1. **Signaling Connection Manager (`gateway/api/src/gateway_api/signaling/manager.py`)**:
   - Manages active room WebSockets, peer lookups, kick callbacks, and JSON broadcasts (< 120 lines).
2. **Signaling Zanzibar Auth (`gateway/api/src/gateway_api/signaling/auth.py`)**:
   - Query param/header credential extraction and SpiceDB Zanzibar session/campaign permission checks (< 90 lines).
3. **Signaling Message Handlers (`gateway/api/src/gateway_api/signaling/handlers.py`)**:
   - Dispatchers for `webrtc_offer`, `webrtc_answer`, `webrtc_ice_candidate`, `webrtc_mute`, and `webrtc_kick` (< 140 lines).
4. **Endpoint Facade (`gateway/api/src/gateway_api/webrtc_signaling.py`)**:
   - Re-exports `WebRTCSignalingManager`, `signaling_manager`, and `voice_signaling_websocket_endpoint` for backward compatibility (< 80 lines).
5. **Test Suite Modularization (`tests/test_blackbox_webrtc_auth.py` and `tests/test_blackbox_webrtc_routing.py`)**:
   - `tests/test_blackbox_webrtc_auth.py`: Connection, credential extraction, and Zanzibar permission rejection (< 180 lines).
   - `tests/test_blackbox_webrtc_routing.py`: SDP offer/answer, ICE candidates, muting, and DM kick actions (< 220 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors internal signaling implementation without altering WebSocket wire protocols, message schemas, or external APIs.
- **Negotiable (N)**: Exact module names and boundaries within `gateway_api/signaling/` can be adjusted.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (< 500 lines) and improves maintainability of live WebRTC infrastructure.
- **Estimable (E)**: Standard Python module extraction and test suite partitioning.
- **Small (S)**: Scope strictly isolated to `gateway_api/` and `tests/test_blackbox_webrtc_signaling.py`; all resulting files < 220 lines.
- **Testable (T)**: Full test coverage verified with `uv run pytest tests/test_blackbox_webrtc*.py`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Modular Submodule Creation**:
   - `manager.py`, `auth.py`, and `handlers.py` created under `gateway/api/src/gateway_api/signaling/`.
   - Endpoint facade in `webrtc_signaling.py` ensures 100% backward compatibility for all existing imports and routes.
2. **Wire Protocol Compatibility**:
   - Zero wire protocol changes: client WebSockets receive identical JSON event payloads.
3. **Strict File Length Compliance (Hard Invariant 6)**:
   - All modified and newly created source files strictly under 250 lines.
4. **Frontdoor Blackbox Verification**:
   - 100% test pass rate on `uv run pytest tests/test_blackbox_webrtc*.py`.
5. **Quality Gates**:
   - Passes `uv run ruff check gateway/api` and `uv run ruff format --check gateway/api`.
