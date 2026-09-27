---
id: '0128'
title: Spatial Companion Mobile WebRTC Audio & Haptic Ping Gateway
status: Refined
created: 2026-09-26
dependencies:
- TASK-0002
- TASK-0033
- TASK-0065
governing_adrs:
- ADR-0002
- ADR-0005
- ADR-0013
governing_prds:
- PRD-0004
governing_stories:
- US-0059
target_release: 0.5.0
---

# TASK-0128: Spatial Companion Mobile WebRTC Audio & Haptic Ping Gateway

## Status
Refined

## Summary
Build a dedicated low-bandwidth WebRTC companion endpoint and mobile WebSocket gateway supporting haptic vibration pulses for secret DM whispers, turn notification alerts, and adaptive Opus voice streaming.

## Problem Statement
Players participating from smartphones or mobile devices suffer from high bandwidth overhead and miss discrete narrative cues (PRD-0004, US-0059). Mobile companions need tactile haptic feedback when The Watcher or DM whispers a secret clue and adaptive bitrate audio that survives cellular fluctuations.

## Governing Architecture & ADRs
- **ADR-0002: Event-Driven Watcher Architecture & Voice Audio**: Low-latency WebAudio and signaling coordination.
- **ADR-0005: Kubernetes-First Infrastructure**: Traefik ingress routing for mobile WebRTC and WebSocket gateways.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Mobile companion presentation components in `services/voice_agent/ui/src/`.

## Product & User Story References
- **Product Requirement**: [`prd-0004-dynamic-vocal-audio-conditioning-and-dsp-filters.md`](../../product/accepted/prd-0004-dynamic-vocal-audio-conditioning-and-dsp-filters.md)
- **User Story**: [`us-0059-spatial-companion-mobile-and-haptic-ping-gateway.md`](../../user_stories/accepted/us-0059-spatial-companion-mobile-and-haptic-ping-gateway.md)

## Detailed Specification & Implementation Plan
1. **Low-Bandwidth Mobile Audio Profile (`services/voice_agent/src/voice_agent/mobile.py`)**:
   - Adaptive Opus mono 16kHz audio stream optimized for high-packet-loss cellular connections.
2. **Haptic Vibration Gateway Protocol**:
   - WebSocket payload dispatching vibration patterns (e.g., `[200, 100, 200]` for secret whispers) utilizing Web Vibration API.
3. **Diegetic Lockscreen Whisper Notifications**:
   - Web Push and local notification triggers for secret DM messages and urgent combat turn prompts.
4. **Frontdoor Blackbox Verification**:
   - Blackbox test suite verifying mobile WebSocket protocol handshake, haptic payload serialization, and audio degradation fallback.

## INVEST Criteria Evaluation
- **Independent (I)**: Operates as an optional mobile gateway endpoint without modifying primary session WebSockets.
- **Negotiable (N)**: Vibration patterns and bitrate thresholds can be tuned.
- **Valuable (V)**: Allows mobile players to stay immersed with discreet physical feedback.
- **Estimable (E)**: Builds on existing WebRTC voice room signaling (TASK-0033).
- **Small (S)**: Scope strictly isolated to `gateway/api/` and `services/voice_agent/`; all files < 300 lines.
- **Testable (T)**: Frontdoor tests verify WebSocket handshake and packet fallback.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Mobile WebSocket Gateway**:
   - `/ws/mobile-companion/{session_id}` route providing haptic message framing and low-bandwidth audio stream.
2. **Frontdoor Blackbox Test Suite**:
   - `tests/test_blackbox_mobile_companion.py` verifying haptic whisper payloads and connection negotiation via public endpoints.
3. **Quality Gates**:
   - Conforms to Hard Invariant 6 (< 500 lines per file).
   - Passes `uv run pytest tests/test_blackbox_mobile_companion.py`.
