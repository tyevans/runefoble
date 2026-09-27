---
id: '0157'
title: DM Live Vocal Modulator and Real-Time NPC Formant DSP Engine
status: Refined
created: 2026-09-26
dependencies:
- TASK-0006
- TASK-0021
- TASK-0065
governing_adrs:
- ADR-0002
- ADR-0003
- ADR-0007
- ADR-0011
governing_prds:
- PRD-0004
governing_stories:
- US-0020
target_release: 0.6.0
---

# TASK-0157: DM Live Vocal Modulator and Real-Time NPC Formant DSP Engine

## Status
Refined

## Summary
Implement real-time DSP pitch and formant shift filters in `services/voice_agent/` allowing DMs to apply NPC vocal transformations ("Ancient Dragon", "Goblin Skulker", "Celestial Spirit") to outgoing WebAudio streams with <50ms processing latency.

## Problem Statement
Voicing diverse NPCs across marathon sessions causes severe vocal strain for DMs. Adding digital signal processing for formant frequency manipulation and pitch scaling directly into the voice pipeline enables rich character portrayal without physical fatigue.

## Governing Architecture & ADRs
- **ADR-0002: Event-Driven Watcher Gameplay Orchestration**: Real-time audio pipeline integration with low latency.
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout in `services/voice_agent/`.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation between DSP models, archetype presets, and live stream processing.
- **ADR-0011: eventsource-py Core Event Sourcing**: Event-sourced `VocalModulatorPresetApplied` and `VoiceFilterToggled` CloudEvents.

## Product & User Story References
- **Product Requirement**: [`prd-0004-voice-streaming-and-dsp-pipeline.md`](../../product/accepted/prd-0004-voice-streaming-and-dsp-pipeline.md)
- **User Story**: [`us-0020-dm-voice-modulation-and-npc-personas.md`](../../user_stories/accepted/us-0020-dm-voice-modulation-and-npc-personas.md)

## Detailed Specification & Implementation Plan
1. **Formant & Pitch Shift DSP Nodes (`services/voice_agent/src/voice_agent/dsp/formants.py`)**:
   - WebAudio/NumPy DSP filter chains for formant scaling, resonance frequency shifting, and pitch octave offsets (< 160 lines).
2. **NPC Vocal Preset Profiles (`services/voice_agent/src/voice_agent/dsp/presets.py`)**:
   - Preset configurations for common creature archetypes (deep dragon resonance, screeching goblin, ethereal echo, robotic construct) (< 120 lines).
3. **Stream Pipeline Filter (`services/voice_agent/src/voice_agent/dsp/pipeline.py`)**:
   - Low-latency PCM stream filter hooked into WebRTC audio track streaming with <50ms processing latency (< 140 lines).
4. **CloudEvents & Domain Models (`libs/runefoble_events/src/runefoble_events/vocal_dsp.py`)**:
   - Define `VocalModulatorPresetAppliedEvent` and `VoiceFilterToggledEvent` (< 80 lines).
5. **Frontdoor API Endpoints (`services/voice_agent/src/voice_agent/routers/vocal_effects.py`)**:
   - `GET /voice/presets`: List all available NPC voice presets.
   - `POST /voice/modulate`: Set active preset or fine-tune pitch/formant parameters on an active stream session.

## INVEST Criteria Evaluation
- **Independent (I)**: Operates independently within `voice_agent` without breaking standard WebRTC audio streaming.
- **Negotiable (N)**: Preset list and parameter ranges can be configured.
- **Valuable (V)**: Prevents vocal strain and enhances roleplaying immersion for Game Masters.
- **Estimable (E)**: Pure DSP audio transformations and FastAPI routing.
- **Small (S)**: Bounded strictly to `services/voice_agent/src/voice_agent/dsp/`; all files < 160 lines.
- **Testable (T)**: Frontdoor blackbox tests verify preset activation and DSP audio frame modifications.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **DSP Engine & Presets**:
   - `services/voice_agent/src/voice_agent/dsp/` created with focused submodules.
   - All modules strictly < 170 lines per Hard Invariant 6.
2. **Frontdoor Test Verification**:
   - Blackbox test suite `tests/test_blackbox_vocal_modulator/` verifies `GET /voice/presets` and `POST /voice/modulate` with synthetic PCM audio frames.
3. **Quality Gates**:
   - Passes `uv run pytest tests/test_blackbox_vocal_modulator/`, `uv run ruff check .`, and `uv run ruff format --check .`.
