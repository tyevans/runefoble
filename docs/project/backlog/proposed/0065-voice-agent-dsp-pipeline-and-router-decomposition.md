---
id: '0065'
title: Voice Agent DSP Pipeline, Audio Routing, and Room Coordinator Modular Decomposition
status: Proposed
created: 2026-09-26
dependencies: [TASK-0006, TASK-0021, TASK-0033]
governing_adrs: [ADR-0002, ADR-0003]
target_release: 0.2.0
---

# TASK-0065: Voice Agent DSP Pipeline, Audio Routing, and Room Coordinator Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/voice_agent/src/voice_agent/dsp.py` (362 lines, 72.4% of limit), `services/voice_agent/src/voice_agent/main.py` (362 lines, 72.4% of limit), and `services/voice_agent/src/voice_agent/room.py` (335 lines, 67.0% of limit) into modular DSP filter chains, phonetic generators, and FastAPI sub-routers before Hard Invariant 6 (File length limit < 500 lines) is breached.

## Problem Statement
The `voice_agent` bounded context contains three core files approaching 400 lines:
1. `services/voice_agent/src/voice_agent/dsp.py` (362 lines) mixes high-level phonetic text mutation rules (drunken slurring regexes, stutters, and hiccup insertions) with low-level 16-bit signed PCM byte/array processing, DSP coefficient math, pitch shifting, reverb delay lines, and pipeline orchestration.
2. `services/voice_agent/src/voice_agent/main.py` (362 lines) bundles FastAPI application instantiation, Redis Streams event bus listeners (`STREAM_SESSION`, `STREAM_VOICE`), speech-to-text endpoints, text-to-speech mock synthesis, and audio conditioning HTTP endpoints.
3. `services/voice_agent/src/voice_agent/room.py` (335 lines) combines room lifecycle tracking, participant state dictionaries, audio stream session orchestration, and kick callbacks.

As real STT (Whisper streaming in TASK-0039) and dynamic ambient soundscapes (TASK-0050) are integrated, these files will easily exceed the 500-line ceiling unless partitioned cleanly into single-responsibility modules.

## Proposed Decomposition
1. **Phonetic Slurring & Text Mutations (`services/voice_agent/src/voice_agent/phonetics.py`)**:
   - Extract regex-based phonetic transforms (`apply_slurred_speech`, stuttering, hiccups) (< 110 lines).
2. **PCM Audio Buffer Filters (`services/voice_agent/src/voice_agent/filters.py`)**:
   - Extract low-level PCM audio filters: pitch shift, reverb convolution, low-pass filter, volume attenuation (< 140 lines).
3. **DSP Pipeline Orchestrator (`services/voice_agent/src/voice_agent/dsp.py`)**:
   - Retain `VoiceDSPPipeline`, `DSPFilterConfig`, and `ProcessedSpeechResult` coordinating phonetics and filters (< 120 lines).
4. **FastAPI Modular Sub-Routers (`services/voice_agent/src/voice_agent/routers/`)**:
   - `routers/audio.py`: Audio conditioning and DSP transformation routes (< 100 lines).
   - `routers/synthesis.py`: STT and TTS synthesis endpoints (< 100 lines).
   - Reduce `voice_agent/main.py` to a clean application bootstrap (< 100 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors internal voice agent module structure without altering external HTTP APIs or Redis Streams event schemas.
- **Negotiable (N)**: Submodule split between phonetics and filter math can be tailored for performance.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (< 500 lines) and prepares `voice_agent` for streaming Whisper model integration.
- **Estimable (E)**: Standard Python refactoring separating text processing, numerical signal processing, and web routers.
- **Small (S)**: Scope strictly isolated to `services/voice_agent/src/voice_agent/`; all resulting files < 150 lines.
- **Testable (T)**: Verified with `uv run pytest tests/test_blackbox_voice_dsp.py tests/test_voice_agent_dsp.py`.

## Acceptance Criteria
1. Full backward compatibility preserved through re-exports in `voice_agent.dsp` and `voice_agent.main`.
2. All modified and newly created source files strictly under 200 lines.
3. 100% test pass rate across all voice agent test suites.
4. Conforms strictly to Hard Invariant 6 (< 500 lines per file).
