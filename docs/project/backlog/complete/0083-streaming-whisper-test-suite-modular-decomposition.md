---
id: 0083
title: Streaming Whisper Audio Transcription Test Suite Modular Decomposition
status: Complete
created: 2026-09-26
dependencies:
- TASK-0039
governing_adrs:
- ADR-0002
- ADR-0007
- ADR-0008
- ADR-0009
target_release: 0.2.0
pr_url: https://github.com/tyevans/runefoble/pull/54
---
# TASK-0083: Streaming Whisper Audio Transcription Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_blackbox_streaming_whisper.py` (423 lines, 84.6% of limit) into shared audio fixtures (`tests/fixtures/audio.py` or helper module) and two focused test suites (`tests/test_blackbox_streaming_whisper_vad.py` and `tests/test_blackbox_streaming_whisper_e2e.py`) to prevent breaching Hard Invariant 6 (File length limit < 500 lines).

## Problem Statement
`tests/test_blackbox_streaming_whisper.py` currently stands at 423 lines, placing it within 77 lines of breaching the 500-line hard invariant ceiling. The file conflates several testing concerns:
1. Synthetic audio waveform and WAV header synthesis utilities (`generate_pcm_sine`, `generate_pcm_silence`, `generate_wav_sine`).
2. Low-level Voice Activity Detection (VAD) tests (silence rejection, speech onset buffering, trailing silence thresholds, WAV container decoding).
3. High-level end-to-end orchestration tests (latency budget benchmarking, continuous WebSocket streaming, speaker buffer isolation, and inter-service Watcher intent routing).

As additional acoustic features (e.g. noise suppression, multi-language speech, speaker diarization) are added, this test suite will rapidly breach 500 lines.

## INVEST Criteria Evaluation
- **Independent (I)**: Splits test suite structure without modifying the voice agent service or Whisper transcription runtime.
- **Negotiable (N)**: Split boundaries between VAD unit/blackbox tests and end-to-end WebSocket tests can be fine-tuned.
- **Valuable (V)**: Safeguards against Hard Invariant 6 violations, speeds up test feedback loops, and clarifies test ownership.
- **Estimable (E)**: Standard pytest suite decomposition with fixture sharing.
- **Small (S)**: Scope strictly isolated to `tests/test_blackbox_streaming_whisper.py`.
- **Testable (T)**: `uv run pytest tests/test_blackbox_streaming_whisper_*.py` verifies 100% test pass rate with zero test regression.

## Governing Architecture & ADRs
- **ADR-0002**: Real-Time Audio Streaming Pipeline and WebRTC Voice Architecture.
- **ADR-0007**: Development Tooling and Local Kind Cluster Workflows.
- **ADR-0008**: Property and Mutation Testing Strategy.
- **ADR-0009**: Code Quality and Linting with Ruff (strict file length invariant < 500 lines).

## Proposed Decomposition
1. **Audio Synthesis Helpers (`tests/helpers/audio_synth.py` or shared fixtures)**:
   - `generate_pcm_sine`, `generate_pcm_silence`, `generate_wav_sine`, and mock bus fixtures (~70 lines).
2. **VAD & Audio Chunking Suite (`tests/test_blackbox_streaming_whisper_vad.py`)**:
   - `test_silence_chunk_rejected_without_events`
   - `test_speech_onset_and_accumulation`
   - `test_sub_250ms_silence_triggers_utterance_and_event`
   - `test_wav_container_ingestion`
   - Target length: < 180 lines.
3. **E2E Latency & WebSocket Suite (`tests/test_blackbox_streaming_whisper_e2e.py`)**:
   - `test_end_to_end_streaming_speech_to_intent_latency_budget`
   - `test_continuous_stream_over_websocket_frontdoor`
   - `test_forced_completion_via_is_final`
   - `test_multi_speaker_buffer_isolation`
   - Target length: < 190 lines.
4. **Original Monolith Deletion**:
   - Remove `tests/test_blackbox_streaming_whisper.py`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Modular Test Suite Creation**:
   - `tests/test_blackbox_streaming_whisper_vad.py` and `tests/test_blackbox_streaming_whisper_e2e.py` created.
   - Original monolithic file removed.
2. **Zero Coverage Loss**:
   - All 8 existing test cases preserved and passing without skipped assertions.
3. **File Length Compliance**:
   - All resulting test files strictly under 250 lines.
4. **Frontdoor Blackbox Verification**:
   - 100% pass rate on `uv run pytest tests/test_blackbox_streaming_whisper_*.py`.
5. **Quality Gate Verification**:
   - Passes `uv run ruff check tests/` and `uv run ruff format --check tests/`.
