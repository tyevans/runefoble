---
id: 0021
title: Real-Time Dynamic DSP Audio Conditioning Pipeline
status: Refined
created: 2026-09-25
dependencies: [TASK-0006]
governing_adrs: [ADR-0002, ADR-0007]
target_release: 0.1.0
---

# TASK-0021 — Real-Time Dynamic DSP Audio Conditioning Pipeline

## Summary
Implement a high-performance dynamic DSP audio conditioning chain in `voice_agent` (US-0011, PRD-0004) supporting filter presets (`drunk`, `whisper`, `underwater`, `ethereal`) with deterministic transformations, sub-50ms processing latency, and domain event dispatch. Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup), test verification must strictly interact through the public HTTP frontdoors (`POST /api/v1/voice/tts`, `POST /api/v1/voice/dsp/apply`), asserting on audio bytes, frequency modulation metadata, and emitted `VoiceAudioConditioned` events.

## Scope & Changes
1. **Domain Events (`libs/runefoble_events/src/runefoble_events/watcher.py`)**:
   - `VoiceAudioConditioned`: `session_id`, `speaker_id`, `speaker_name`, `filters_applied`, `latency_ms`, `audio_bytes_length`. (@register_event("runefoble.events.voice.audio_conditioned"))
2. **DSP Filter Chain (`services/voice_agent/src/voice_agent/dsp.py`)**:
   - Add filter presets (`whisper`, `underwater`, `ethereal`, `drunk`) with fast numpy/scipy-free or pure Python math operations guaranteeing sub-50ms execution.
3. **Public Frontdoor Endpoints (`services/voice_agent/src/voice_agent/main.py`)**:
   - `POST /api/v1/voice/dsp/apply`
   - Update `POST /api/v1/voice/tts` to accept `filters: list[str]`.
4. **Blackbox TDD Suite (`tests/test_blackbox_voice_dsp.py`)**:
   - Test client interactions strictly through FastAPI `TestClient(app)` from `voice_agent.main`.
   - Measure execution latency (<50ms).
   - Validate transform parameters and event dispatch.
5. **PRD & Backlog Maintenance**:
   - Update `docs/project/product/accepted/prd-0004-dynamic-vocal-audio-conditioning-and-dsp-filters.md`.
   - Update `PRIORITY.md` and move card to `complete/`.
