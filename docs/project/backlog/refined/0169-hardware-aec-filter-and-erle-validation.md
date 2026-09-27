---
id: '0169'
title: Hardware Acoustic Echo Cancellation and ERLE Validation
status: Refined
created: 2026-09-26
dependencies:
- TASK-0141
governing_adrs:
- ADR-0002
- ADR-0003
- ADR-0006
- ADR-0007
governing_prds:
- PRD-0020
governing_stories:
- US-0060
target_release: 0.7.0
---

# TASK-0169: Hardware Acoustic Echo Cancellation and ERLE Validation

## Status
Refined

## Summary
Implement adaptive acoustic echo cancellation (AEC) filtering in `services/voice_agent/`, isolating incoming player vocal audio from outgoing room loudspeaker playback to ensure >35dB Echo Return Loss Enhancement (ERLE) without audible voice distortion.

## Problem Statement
Tabletop players using desktop speakers rather than headsets experience acoustic feedback loops where AI speech bleeds into the microphone, creating echo loops and triggering false speech-to-intent parses.

## Governing Architecture & ADRs
- **ADR-0002: Event-Driven Watcher Gameplay Orchestration**: Real-time voice stream lifecycle and duplex responsiveness.
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Dedicated DSP filtering submodules in `services/voice_agent/src/voice_agent/aec/`.
- **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Diagnostic AEC metric streaming to `runefoble:events:voice`.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation for audio signal filtering and echo mitigation.

## Product & User Story References
- **Product Requirement**: [`prd-0020-zero-latency-neural-voice-duplex.md`](../../product/accepted/prd-0020-zero-latency-neural-voice-duplex.md)
- **User Story**: [`us-0060-zero-latency-neural-voice-duplex.md`](../../user_stories/accepted/us-0060-zero-latency-neural-voice-duplex.md)

## Detailed Specification & Implementation Plan
1. **Normalized Least Mean Squares (NLMS) AEC Filter (`services/voice_agent/src/voice_agent/aec/nlms_filter.py`)**:
   - Adaptive transversal filter computing loudspeaker transfer functions and canceling echo signals (< 150 lines).
2. **Double-Talk Detector & Residual Echo Suppressor (`services/voice_agent/src/voice_agent/aec/double_talk.py`)**:
   - State machine preventing filter divergence during simultaneous human and AI speech (< 130 lines).
3. **CloudEvents Registration (`libs/runefoble_events/src/runefoble_events/aec.py`)**:
   - Define `EchoSuppressionEngagedEvent` and `AECBenchmarkCompletedEvent` (< 70 lines).
4. **Diagnostic REST Endpoint (`services/voice_agent/src/voice_agent/routers/aec_diagnostics.py`)**:
   - `POST /voice/aec/benchmark`: Feed paired loudspeaker and microphone PCM streams to validate ERLE > 35dB (< 120 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Operates strictly at the audio input preprocessing stage before speech transcription.
- **Negotiable (N)**: NLMS adaptation step size and filter length can be tuned for different room reverberation models.
- **Valuable (V)**: Enables players to use open tabletop speaker setups without speech recognition feedback loops.
- **Estimable (E)**: Standard DSP algorithms with quantifiable ERLE metrics.
- **Small (S)**: Bounded strictly to `services/voice_agent/src/voice_agent/aec/`; all modules < 160 lines.
- **Testable (T)**: Frontdoor blackbox tests verify echo suppression >35dB across synthetic room profiles.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **AEC Filter Architecture**:
   - `services/voice_agent/src/voice_agent/aec/` created with focused submodules.
   - All modules strictly < 160 lines per Hard Invariant 6.
2. **Frontdoor Test Verification**:
   - Blackbox test suite `tests/test_blackbox_aec_filter/` verifies >35dB ERLE and zero false intent triggers during loudspeaker playback.
3. **Quality Gates**:
   - Passes `uv run pytest tests/test_blackbox_aec_filter/`, `uv run ruff check .`, and `uv run ruff format --check .`.
