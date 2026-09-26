---
id: '0065'
title: Voice Agent DSP Pipeline, Audio Routing, and Room Coordinator Modular Decomposition
status: Refined
created: 2026-09-26
dependencies:
- TASK-0006
- TASK-0021
- TASK-0033
governing_adrs:
- ADR-0002
- ADR-0003
- ADR-0007
- ADR-0009
target_release: 0.2.0
---

# TASK-0065: Voice Agent DSP Pipeline, Audio Routing, and Room Coordinator Modular Decomposition

## Status
Refined

## Summary
Decompose `services/voice_agent/src/voice_agent/dsp.py` (373 lines, 74.6% of limit), `services/voice_agent/src/voice_agent/main.py` (384 lines, 76.8% of limit), and `services/voice_agent/src/voice_agent/room.py` (335 lines, 67.0% of limit) into modular DSP filter chains, phonetic generators, and FastAPI sub-routers before Hard Invariant 6 (File length limit < 500 lines) is breached.

## Problem Statement
The `voice_agent` bounded context contains three core files approaching 400 lines:
1. `services/voice_agent/src/voice_agent/dsp.py` (373 lines) mixes high-level phonetic text mutation rules (drunken slurring regexes, stutters, and hiccup insertions) with low-level 16-bit signed PCM byte/array processing, DSP coefficient math, pitch shifting, reverb delay lines, and pipeline orchestration.
2. `services/voice_agent/src/voice_agent/main.py` (384 lines) bundles FastAPI application instantiation, Redis Streams event bus listeners, speech-to-text endpoints, text-to-speech mock synthesis, and audio conditioning HTTP endpoints.
3. `services/voice_agent/src/voice_agent/room.py` (335 lines) combines room lifecycle tracking, participant state dictionaries, audio stream session orchestration, and kick callbacks.

As real STT (Whisper streaming in TASK-0039) and dynamic ambient soundscapes (TASK-0050) are integrated, these files will easily exceed the 500-line ceiling unless partitioned cleanly into single-responsibility modules.

## Governing Architecture & ADRs
- **ADR-0002**: The Watcher Autonomous DM (voice persona synthesis).
- **ADR-0003**: UV Monorepo Workspace for Python Bounded Contexts.
- **ADR-0007**: Real-Time Voice and Board Synchronization (DSP audio pipeline).
- **ADR-0009**: Continuous Backlog Refinement and Technical Debt Management.

## Proposed Decomposition
1. **Phonetic Slurring & Text Mutations (`services/voice_agent/src/voice_agent/phonetics.py`)**:
   - Extract regex-based phonetic transforms (`apply_slurred_speech`, stuttering, hiccups) (< 110 lines).
2. **PCM Audio Buffer Filters (`services/voice_agent/src/voice_agent/filters.py`)**:
   - Extract low-level PCM audio filters: pitch shift, reverb convolution, low-pass filter, volume attenuation (< 140 lines).
3. **DSP Pipeline Orchestrator (`services/voice_agent/src/voice_agent/dsp.py`)**:
   - Retain `VoiceDSPPipeline`, `DSPFilterConfig`, and `ProcessedSpeechResult` coordinating phonetics and filters (< 140 lines).
4. **FastAPI Modular Sub-Routers (`services/voice_agent/src/voice_agent/routers/`)**:
   - `routers/audio.py`: Audio conditioning and DSP transformation routes (< 120 lines).
   - `routers/synthesis.py`: STT and TTS synthesis endpoints (< 120 lines).
   - Reduce `voice_agent/main.py` to a clean application bootstrap (< 100 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors internal voice agent module structure without altering external HTTP APIs or Redis Streams event schemas.
- **Negotiable (N)**: Submodule split between phonetics and filter math can be tailored for performance.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (< 500 lines) and prepares `voice_agent` for streaming Whisper model integration.
- **Estimable (E)**: Standard Python refactoring separating text processing, numerical signal processing, and web routers.
- **Small (S)**: Scope strictly isolated to `services/voice_agent/src/voice_agent/`; all resulting files < 150 lines.
- **Testable (T)**: Verified with `uv run pytest tests/test_blackbox_voice_dsp.py tests/test_voice_agent_dsp.py`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Modular Submodule Creation**:
   - `phonetics.py` and `filters.py` created with clean separation of text transforms and PCM audio processing.
   - Modular routers created in `services/voice_agent/src/voice_agent/routers/`.
2. **Re-Export Backward Compatibility**:
   - Full backward compatibility preserved through re-exports in `voice_agent.dsp` and `voice_agent.main`.
3. **Strict File Length Compliance (Hard Invariant 6)**:
   - All modified and newly created source files strictly under 200 lines.
4. **Frontdoor Blackbox Verification**:
   - 100% test pass rate on `uv run pytest tests/test_blackbox_voice_dsp.py tests/test_voice_agent_dsp.py`.
5. **Quality Gates**:
   - Passes `uv run ruff check services/voice_agent` and `uv run ruff format --check services/voice_agent`.
