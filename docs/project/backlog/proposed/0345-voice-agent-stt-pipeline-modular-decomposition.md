---
id: '0345'
title: Voice Agent STT Pipeline Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0039
- TASK-0083
governing_adrs:
- ADR-0002
- ADR-0003
- ADR-0006
- ADR-0013
governing_prds:
- PRD-0004
- PRD-0020
governing_stories:
- US-0020
- US-0060
target_release: 0.8.0
---

# TASK-0345: Voice Agent STT Pipeline Modular Decomposition

## Status
Proposed

## Summary
Decompose `services/voice_agent/src/voice_agent/stt.py` (279 lines, 55.8% of limit) into modular submodules under `services/voice_agent/src/voice_agent/stt/` (`models.py`, `pipeline.py`, `broadcaster.py`), with an aggregator export at `services/voice_agent/src/voice_agent/stt.py`, ensuring all submodules remain strictly < 110 lines per Hard Invariant 6.

## Problem Statement
`services/voice_agent/src/voice_agent/stt.py` combines Pydantic model definitions (`ChunkProcessingResult`), participant audio ring buffers, VAD silence tracking, Whisper acoustic inference dispatch, and Redis Streams event broadcasting in a single monolithic module. As multilingual speech models, custom acoustic models, and directional microphone stream separation are added, this file will approach the 500-line limit unless modularized into focused components.

## Governing Architecture & ADRs
- **ADR-0002: Real-Time Audio Streaming Architecture**: Sub-500ms voice pipeline.
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout.
- **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Real-time event propagation and stream broadcasting.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 110 lines).

## Scope of Work
1. **Audio State Models (`services/voice_agent/src/voice_agent/stt/models.py`)**:
   - Extract `ChunkProcessingResult`, `ParticipantAudioState`, and UUID conversion helpers (< 50 lines).
2. **Audio Processing Pipeline (`services/voice_agent/src/voice_agent/stt/pipeline.py`)**:
   - Extract `StreamingAudioPipeline` ingestion loop and VAD chunk processing (< 100 lines).
3. **Event Broadcaster (`services/voice_agent/src/voice_agent/stt/broadcaster.py`)**:
   - Extract Redis Streams `PlayerSpokeEvent` construction and dispatching logic (< 60 lines).
4. **Aggregator Entry Point (`services/voice_agent/src/voice_agent/stt.py`)**:
   - Re-export all pipeline classes and global singleton helpers for backwards compatibility (< 35 lines).
5. **Verification**:
   - Ensure `uv run pytest tests/test_blackbox_voice_agent.py` and all voice tests pass with zero regressions.

## Definition of Done
- `services/voice_agent/src/voice_agent/stt/` submodules strictly < 110 lines each per Hard Invariant 6.
- Root `stt.py` reduced to a backwards-compatible re-export module (< 40 lines).
- Passes all tests via `uv run pytest`.
- Code passes `uv run ruff check .` and `uv run ruff format --check .`.
