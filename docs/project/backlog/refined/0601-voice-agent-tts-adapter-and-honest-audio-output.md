---
id: '0601'
title: Voice Agent TTS Adapter Port and Honest Synthesis Output
status: Refined
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0002
- ADR-0003
- ADR-0007
- ADR-0014
governing_prds:
- PRD-0004
- PRD-0020
governing_stories:
- US-0020
- US-0060
target_release: 0.9.0
severity: high
source_audits:
- w2-voice-agent.md
---

# TASK-0601: Voice Agent TTS Adapter Port and Honest Synthesis Output

## Status
Refined

## Summary
The synthesis route does not synthesise speech. It applies filters to `None`, which produces a 50 ms 220 Hz tone for any text. The reported duration is a formula. The `audio_stream_url` points to routes that do not exist. This task adds a TTS port with a real production adapter, makes the response describe the audio it returns, and removes dead URLs.

## Problem Statement
- `services/voice_agent/src/voice_agent/routers/synthesis.py` near line 63-64 calls `apply_audio_filters(None, filters)`. `filters.py` then calls `generate_synthetic_audio(0.05)` (`audio_utils.py`).
- The output is 1600 bytes for a 40-character text. It does not depend on the text.
- `synthesis.py` near line 70 sets `duration_ms = max(1200, len(text) * 65)`. This does not match the audio (the probe returned 2860 ms for 1600 bytes).
- `synthesis.py:73` and `routers/audio.py:47` return `/streams/audio/...` and `/streams/dsp/...`. No such routes exist. The URL uses `abs(hash(...))`, which changes between processes.
- No speech engine is referenced anywhere in the service.

Source: `.audit/reports/w2-voice-agent.md` F4.

## Documentation & Architecture Review
- `docs/how-to/modulate-dm-vocal-npc-presets.md` and `docs/how-to/handle-neural-voice-duplex-and-speech-interruption.md` describe real TTS output. They must match the result of this task.
- TASK-0464 (proposed, voice-cloned stand-in dialogue) needs a base TTS adapter. This task unblocks it. TASK-0464 is not superseded.
- ADR-0007: TTS engine is an adapter behind a port.

## Product & User Story References
- `docs/project/product/accepted/prd-0004-dynamic-vocal-audio-conditioning-and-dsp-filters.md`
- `docs/project/product/accepted/prd-0020-zero-latency-neural-voice-duplex-and-interruption.md`
- `docs/project/user_stories/accepted/us-0020-dm-vocal-modulator-with-realtime-npc-filtering.md`

## Detailed Specification & Implementation Plan
1. Define a `TextToSpeech` port with `synthesize(text, voice) -> AudioClip` where `AudioClip` carries PCM bytes, sample rate, and measured duration.
2. Add `VoiceAgentSettings.tts_engine` with a real default. Use `mock` only when a test sets it.
3. The synthesis route returns the audio it describes. Inline the audio as base64 in the response, or serve it from a real route. Remove the dead URL fields.
4. Duration is computed from the sample count and sample rate.
5. DSP filters run on the synthesised clip only, never on `None`.
6. Engine failure returns HTTP 503 with an error body. No tone is returned.
7. Update the reference docs for the response schema.

## Frontdoor Blackbox Test Plan
- Before fix: POST two texts of different length to the synthesis route. Both return the same 1600-byte tone (test fails).
- After fix: the returned audio length grows with text length under the test engine. The duration equals `samples / sample_rate` within 1 ms (test passes).
- After fix: no response field contains `/streams/`. Two calls for the same text return the same content hash.
- After fix: with the engine forced unavailable, the route returns 503 and no audio.

## Definition of Done
1. No code path calls `apply_audio_filters(None, ...)`. No production code calls `generate_synthetic_audio`.
2. TTS port and adapter in place. Files under 500 lines.
3. Blackbox tests pass. `uv run pytest services/voice_agent` passes.
4. Ruff check and format pass.
5. Reference docs updated. `CHANGELOG.md` `[Unreleased]` entry added.
