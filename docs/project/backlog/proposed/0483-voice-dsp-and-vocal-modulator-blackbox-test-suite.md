---
id: '0483'
title: DM Vocal Modulation and Voice DSP Frontdoor Blackbox Test Suite
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0480
- TASK-0481
- TASK-0482
governing_adrs:
- ADR-0001
- ADR-0002
- ADR-0005
- ADR-0010
governing_prds:
- PRD-0004
governing_stories:
- US-0011
- US-0020
target_release: 0.9.0
---

# TASK-0483: DM Vocal Modulation and Voice DSP Frontdoor Blackbox Test Suite

## Status
Proposed

## Summary
Author a comprehensive blackbox integration test suite (`tests/test_blackbox_voice_dsp_and_vocal_modulator.py`) validating the full voice DSP lifecycle exclusively through public frontdoors: Gateway API routes (`/api/v1/voice/presets`, `/api/v1/voice/modulate`, `/api/v1/voice/dsp/apply`), SpiceDB Zanzibar permission checks (`control` / `participate`), audio frame processing latency SLAs (<50ms), and event dispatch to Redis Streams.

## Problem Statement
While individual unit tests exist for voice agent DSP utilities, there is no end-to-end blackbox test suite exercising the vocal modulation and audio conditioning pipeline through the Gateway API. We must ensure that unauthenticated calls are rejected with 401, non-DM users attempting DM-only voice modulation are rejected with 403 by SpiceDB Zanzibar, and audio processing latency adheres to the strict <50ms SLA defined in PRD-0004.

## Governing Architecture & ADRs
- **ADR-0001: Google Zanzibar for Fine-Grained Authorization**: Verifying permission enforcement across session roles through public HTTP responses.
- **ADR-0002: Real-Time Audio Architecture**: Verifying sub-500ms pipeline and sub-50ms DSP latency limits.
- **ADR-0010: Continuous Integration Pipeline**: Fast, reliable execution under `pytest` with frontdoor setup per Hard Invariant 7.

## Product & User Story References
- [`prd-0004-dynamic-vocal-audio-conditioning-and-dsp-filters.md`](../../product/accepted/prd-0004-dynamic-vocal-audio-conditioning-and-dsp-filters.md)
- [`us-0011-dynamic-voice-filters-for-afflicted-characters.md`](../../user_stories/accepted/us-0011-dynamic-voice-filters-for-afflicted-characters.md)
- [`us-0020-dm-vocal-modulator-with-realtime-npc-filtering.md`](../../user_stories/accepted/us-0020-dm-vocal-modulator-with-realtime-npc-filtering.md)

## Scope of Work
1. **Test Fixtures & Setup (`tests/test_blackbox_voice_dsp_and_vocal_modulator.py`)**:
   - Set up test sessions, DM user credentials, and player user credentials through public Gateway routes.
   - Generate synthetic 16kHz PCM audio test frames.
2. **API Contract & Preset Enumeration Tests**:
   - Assert `GET /api/v1/voice/presets` returns the four canonical presets with valid pitch, formant, and resonance specs.
3. **Zanzibar Permission Enforcement Tests**:
   - Assert DM user can successfully execute `POST /api/v1/voice/modulate`.
   - Assert non-member user receives 403 Forbidden.
   - Assert unauthenticated request receives 401 Unauthorized.
4. **DSP Conditioning & Latency SLA Tests**:
   - Measure execution duration of `POST /api/v1/voice/dsp/apply` across `drunk`, `underwater`, `whisper`, and `ethereal` filters, asserting processing latency strictly < 50ms.
   - Verify returned audio payload contains valid non-empty base64 audio frames.
5. **Event Dispatch Assertions**:
   - Verify `VoiceAudioConditioned` CloudEvents are emitted to the event bus upon DSP transformation.

## Definition of Done
1. `tests/test_blackbox_voice_dsp_and_vocal_modulator.py` implemented and passing with 100% assertions via `uv run pytest`.
2. All test setup and assertions interact strictly through public HTTP frontdoors per Hard Invariant 7.
3. Processing latency SLA (<50ms) is asserted deterministically.
4. Test suite conforms strictly to Hard Invariant 6 (< 500 lines).
