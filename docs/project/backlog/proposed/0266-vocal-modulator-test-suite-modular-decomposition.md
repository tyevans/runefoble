---
id: '0266'
title: Vocal Modulator Blackbox Test Suite Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0157
governing_adrs:
- ADR-0002
- ADR-0003
- ADR-0007
- ADR-0011
governing_prds:
- PRD-0004
governing_stories:
- US-0020
target_release: 0.8.0
---

# TASK-0266: Vocal Modulator Blackbox Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_blackbox_vocal_modulator/test_vocal_modulator.py` (306 lines) into modular submodules within `tests/test_blackbox_vocal_modulator/` (`test_vocal_presets.py`, `test_dsp_formant_filters.py`, `test_voice_room_integration.py`), maintaining all files strictly < 120 lines.

## Problem Statement
`tests/test_blackbox_vocal_modulator/test_vocal_modulator.py` tests preset configuration, real-time DSP formant shifting, and voice room coordinator event propagation in a single monolithic test file. As neural duplex barge-in and adaptive Opus streaming tests are introduced, this file will exceed the 500-line invariant limit unless modularized.

## Governing Architecture & ADRs
- **ADR-0002: Event-Driven Watcher Gameplay Orchestration**: Voice DSP and audio streaming pipelines.
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean test module structuring.
- **ADR-0007: Domain-Driven Design Architecture**: Voice agent bounded context segregation.
- **ADR-0011: eventsource-py Core Event Sourcing**: Event-sourced preset and filter state transitions.

## Scope of Work
1. **Shared Fixtures (`tests/test_blackbox_vocal_modulator/conftest.py`)**:
   - Extract test client setup, mock SpiceDB authorization, and synthetic audio generation helpers (< 50 lines).
2. **Preset Application Tests (`tests/test_blackbox_vocal_modulator/test_vocal_presets.py`)**:
   - Extract preset selection (dragon, goblin, ethereal, dwarf) and parameter mapping tests (< 95 lines).
3. **DSP Formant Filter Tests (`tests/test_blackbox_vocal_modulator/test_dsp_formant_filters.py`)**:
   - Extract pitch shifting, formant warping, and DSP audio buffer transform tests (< 95 lines).
4. **Voice Room Event Tests (`tests/test_blackbox_vocal_modulator/test_voice_room_integration.py`)**:
   - Extract voice room coordinator event emission and multi-track audio routing tests (< 90 lines).
5. **Verification**:
   - Run `uv run pytest tests/test_blackbox_vocal_modulator/` and verify clean execution.

## Definition of Done
- `tests/test_blackbox_vocal_modulator/` decomposed into focused submodules strictly < 120 lines.
- All test cases pass via `uv run pytest tests/test_blackbox_vocal_modulator/`.
- Zero lint or formatting errors (`uv run ruff check .` and `uv run ruff format --check .`).
