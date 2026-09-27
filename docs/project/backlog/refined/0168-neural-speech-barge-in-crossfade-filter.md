---
id: '0168'
title: Neural Speech Barge-In and Soft Crossfade Audio Filter
status: Refined
created: 2026-09-26
dependencies:
- TASK-0141
governing_adrs:
- ADR-0002
- ADR-0003
- ADR-0007
governing_prds:
- PRD-0020
governing_stories:
- US-0060
target_release: 0.7.0
---

# TASK-0168: Neural Speech Barge-In and Soft Crossfade Audio Filter

## Status
Refined

## Summary
Implement high-precision voice activity onset detection with 20ms cosine soft crossfading in `services/voice_agent/`, halting AI TTS audio streams within 80ms of human interjection without audible pops or clicks.

## Problem Statement
Abrupt audio clipping during conversational barge-in sounds harsh and unnatural, while delayed cutoffs cause AI speech to clash loudly with human speech for several syllables.

## Governing Architecture & ADRs
- **ADR-0002: Event-Driven Watcher Gameplay Orchestration**: Real-time voice stream lifecycle and duplex responsiveness.
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean DSP audio modules in `services/voice_agent/`.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation for audio filters and voice activity events.

## Product & User Story References
- **Product Requirement**: [`prd-0020-zero-latency-neural-voice-duplex.md`](../../product/accepted/prd-0020-zero-latency-neural-voice-duplex.md)
- **User Story**: [`us-0060-neural-voice-duplex-and-barge-in.md`](../../user_stories/accepted/us-0060-neural-voice-duplex-and-barge-in.md)

## Detailed Specification & Implementation Plan
1. **Low-Latency VAD Onset Hook (`services/voice_agent/src/voice_agent/dsp/barge_in_filter.py`)**:
   - Audio ring-buffer evaluator detecting vocalization onset in under 40ms (< 140 lines).
2. **Smooth Cosine Crossfade Attenuator (`services/voice_agent/src/voice_agent/dsp/cosine_crossfade.py`)**:
   - 20ms soft-fade filter damping outgoing TTS PCM samples gracefully to silence (< 120 lines).
3. **CloudEvents Registration (`libs/runefoble_events/src/runefoble_events/voice_barge_in.py`)**:
   - Define `NeuralSpeechBargeInDetectedEvent` and `TTSStreamAttenuatedEvent` (< 70 lines).
4. **Frontdoor Audio Diagnostic API (`services/voice_agent/src/voice_agent/routers/audio_filters.py`)**:
   - `POST /voice/filters/barge-in/evaluate`: Feed synthetic audio frames to evaluate interruption onset and attenuation timing (< 130 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Functions independently on the voice audio pipeline without blocking text or board state updates.
- **Negotiable (N)**: Cosine attenuation curve duration (10ms-30ms) is configurable.
- **Valuable (V)**: Eliminates jarring audio clipping when players interrupt AI dialogue.
- **Estimable (E)**: Pure PCM sample attenuation and VAD integration.
- **Small (S)**: Bounded strictly to `services/voice_agent/src/voice_agent/dsp/`; all files < 160 lines.
- **Testable (T)**: Frontdoor blackbox tests verify sub-80ms halt time with zero waveform discontinuity artifacts.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **DSP Filter Architecture**:
   - `services/voice_agent/src/voice_agent/dsp/` created with focused submodules.
   - All modules strictly < 160 lines per Hard Invariant 6.
2. **Frontdoor Test Verification**:
   - Blackbox test suite `tests/test_blackbox_barge_in_filter/` asserts interruption halt latency < 80ms and smooth cosine damping.
3. **Quality Gates**:
   - Passes `uv run pytest tests/test_blackbox_barge_in_filter/`, `uv run ruff check .`, and `uv run ruff format --check .`.
