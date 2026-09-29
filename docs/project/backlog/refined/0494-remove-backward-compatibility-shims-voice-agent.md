---
id: '0494'
title: Remove Backward Compatibility Shims & Re-exports in voice_agent
status: Refined
created: 2026-09-29
dependencies:
- TASK-0006
- TASK-0021
- TASK-0033
governing_adrs:
- ADR-0003
- ADR-0007
- ADR-0010
governing_prds:
- PRD-0007
governing_stories:
- US-0007
- US-0020
target_release: 0.9.0
---

# TASK-0494: Remove Backward Compatibility Shims & Re-exports in voice_agent

## Status
Refined

## Summary
Decommission `voice_agent/room.py` aggregator facade, excise backward-compatibility method aliases in `phonetics.py` and `audio_utils.py`, migrate call sites to modular subpackages, and remove obsolete backward-compatibility assertions from `tests/test_voice_agent_dsp.py`.

## Problem Statement
In `services/voice_agent`:
- `src/voice_agent/room.py` exists as a 32-line facade re-exporting room aggregates, state models, and coordinator for backward compatibility.
- `src/voice_agent/phonetics.py` retains a backward-compatibility alias `apply_slurred_speech` for canonical phonetic slurring.
- `src/voice_agent/audio_utils.py` retains a private alias for `to_samples_array` for backward compatibility.
- `tests/test_voice_agent_dsp.py:test_backward_compatible_reexports` actively tests backward-compatible re-exports from `voice_agent.dsp` and `voice_agent.room`.
These artifacts represent legacy debt violating the updated DoR.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/explanation/realtime-voice-and-board-sync.md`: Audio streaming pipeline architecture.
  - `docs/how-to/modulate-dm-vocal-npc-presets.md`: DSP filters and voice presets.
- **Governing Architecture & ADRs**:
  - **ADR-0007: Speech-to-Intent Pipeline**: Audio streaming and voice recognition.
  - **ADR-0010: Real-Time Audio Pipeline**: Room audio coordinator and WebRTC integration.

## Product & User Story References
- [`prd-0007-realtime-voice-streaming-and-dsp.md`](../../product/accepted/prd-0007-realtime-voice-streaming-and-dsp.md)
- [`us-0007-voice-streaming-audio-pipeline.md`](../../user_stories/accepted/us-0007-voice-streaming-audio-pipeline.md)
- [`us-0020-voice-dsp-conditioning-filters.md`](../../user_stories/accepted/us-0020-voice-dsp-conditioning-filters.md)

## Detailed Specification & Implementation Plan
1. **Decommission Room Facade**:
   - Delete or refactor `services/voice_agent/src/voice_agent/room.py` to route callers directly to `voice_agent.room.*` (room aggregates, coordinator, models).
2. **Remove Function and Utility Aliases**:
   - In `services/voice_agent/src/voice_agent/phonetics.py`, remove the `apply_slurred_speech` alias, standardizing callers on the canonical function name.
   - In `services/voice_agent/src/voice_agent/audio_utils.py`, remove the backward-compatibility alias for `to_samples_array`.
3. **Migrate Import Sites Across Voice Agent**:
   - Update `voice_agent/main.py`, room routes, and tests to import from authoritative submodules (`voice_agent.dsp.*`, `voice_agent.room.*`, `voice_agent.webrtc.*`).
4. **Update Blackbox Test Suites**:
   - In `tests/test_voice_agent_dsp.py`, delete `test_backward_compatible_reexports()`.
   - Ensure all DSP and voice agent tests pass against direct modular imports.

## INVEST Criteria Evaluation
- **Independent (I)**: Changes are strictly confined to `services/voice_agent` and its test suite.
- **Negotiable (N)**: Clean standard Python package hierarchy.
- **Valuable (V)**: Cleans up audio processing pipeline and deletes dead facade code.
- **Estimable (E)**: Clearly identified files (`room.py`, `phonetics.py`, `audio_utils.py`).
- **Small (S)**: File changes well under 500 lines per file.
- **Testable (T)**: Verified via `uv run pytest tests/test_voice_agent*`.

## Definition of Done
1. `room.py` facade retired and call sites migrated.
2. Function aliases removed from `phonetics.py` and `audio_utils.py`.
3. Obsolete facade re-export tests removed from `tests/test_voice_agent_dsp.py`.
4. All voice agent tests pass with zero warnings.
