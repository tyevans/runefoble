---
id: '0166'
title: Mobile Low-Bandwidth Opus Adaptive Stream Adapter
status: Complete
created: 2026-09-26
dependencies:
- TASK-0128
governing_adrs:
- ADR-0002
- ADR-0003
- ADR-0006
governing_prds:
- PRD-0019
governing_stories:
- US-0059
target_release: 0.7.0
pr_url: https://github.com/tyevans/runefoble/pull/210
---
# TASK-0166: Mobile Low-Bandwidth Opus Adaptive Stream Adapter

## Status
Refined

## Summary
Implement network-adaptive WebRTC stream bitrate scaling in `services/voice_agent/`, automatically stepping audio transmission down to 16kHz mono Opus (<50 kbps) when mobile participants experience packet loss.

## Problem Statement
Players connecting via mobile cellular networks suffer severe audio stuttering and disconnections during high-latency or packet-constrained intervals when high-definition stereo streams are mandated.

## Governing Architecture & ADRs
- **ADR-0002: Event-Driven Watcher Gameplay Orchestration**: Real-time voice stream lifecycle and low-latency adaptation.
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout in `services/voice_agent/`.
- **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Diagnostic stream quality event emission.

## Product & User Story References
- **Product Requirement**: [`prd-0019-mobile-companion-and-spatial-haptics.md`](../../product/accepted/prd-0019-mobile-companion-and-spatial-haptics.md)
- **User Story**: [`us-0059-mobile-companion-and-haptic-alerts.md`](../../user_stories/accepted/us-0059-mobile-companion-and-haptic-alerts.md)

## Detailed Specification & Implementation Plan
1. **Network Quality Monitor (`services/voice_agent/src/voice_agent/webrtc/quality_monitor.py`)**:
   - WebRTC RTCP receiver report analyzer detecting packet loss (>5%) and round-trip delay spikes within 100ms (< 140 lines).
2. **Adaptive Bitrate Regulator (`services/voice_agent/src/voice_agent/webrtc/adaptive_bitrate.py`)**:
   - Dynamic Opus codec parameter adjustment reducing complexity and bitrate while preserving voice intelligibility (< 130 lines).
3. **CloudEvents Registration (`libs/runefoble_events/src/runefoble_events/voice_stream_quality.py`)**:
   - Define `VoiceStreamQualityDegradedEvent` and `VoiceStreamCodecAdaptedEvent` (< 80 lines).
4. **Diagnostic API Endpoints (`services/voice_agent/src/voice_agent/routers/stream_diagnostics.py`)**:
   - `GET /voice/streams/{session_id}/quality`: Query stream bitrate, packet loss, and codec mode (< 120 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Modulates individual stream bitrates without impacting other participants in the voice room.
- **Negotiable (N)**: Thresholds for packet loss step-down and recovery are configurable.
- **Valuable (V)**: Keeps remote and mobile players connected even under spotty cellular connectivity.
- **Estimable (E)**: Standard RTCP metric evaluation and Opus encoder parameter adjustments.
- **Small (S)**: Bounded strictly to `services/voice_agent/src/voice_agent/webrtc/`; all files < 160 lines.
- **Testable (T)**: Frontdoor blackbox tests verify bitrate step-down under simulated network loss.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Adaptive Architecture**:
   - `services/voice_agent/src/voice_agent/webrtc/` created with focused submodules.
   - All modules strictly < 160 lines per Hard Invariant 6.
2. **Frontdoor Test Verification**:
   - Blackbox test suite `tests/test_blackbox_adaptive_stream/` asserts bitrate reduction within 200ms of simulated packet loss.
3. **Quality Gates**:
   - Passes `uv run pytest tests/test_blackbox_adaptive_stream/`, `uv run ruff check .`, and `uv run ruff format --check .`.
