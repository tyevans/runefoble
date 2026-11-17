---
id: '0600'
title: Voice Agent Production STT Adapter Port (Replace Canned Transcript Default)
status: Complete
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
- US-0001
- US-0060
target_release: 0.9.0
severity: critical
source_audits:
- w2-voice-agent.md
---

# TASK-0600: Voice Agent Production STT Adapter Port (Replace Canned Transcript Default)

## Status
Complete

## Summary
The voice agent default speech-to-text adapter is a mock that returns the fixed phrase "I move 3 squares north". Replace the default with a configured STT port. The production default is a real engine. The mock is used only by test fixtures. When the engine is unavailable, the audio chunk fails with an explicit error event.

## Problem Statement
- `services/voice_agent/src/voice_agent/stt.py:102` sets the default transcriber to `MockWhisperTranscriber()`.
- `services/voice_agent/src/voice_agent/transcriber.py:24` sets `default_transcript = "I move 3 squares north"`.
- `transcriber.py:85` returns the same string when the faster-whisper model fails to load.
- No code in `services/`, `gateway/`, `libs/` or `tests/` selects `FasterWhisperTranscriber`.
- Every utterance without `mock_transcript` becomes the canned phrase. The phrase is forwarded to The Watcher (`stt.py` near lines 225-245). Players see actions they did not speak.

Source: `.audit/reports/w2-voice-agent.md` F1.

## Documentation & Architecture Review
- `docs/explanation/realtime-voice-and-board-sync.md`: sub-500 ms speech pipeline. A canned transcript breaks the speech-to-board contract.
- `docs/how-to/handle-neural-voice-duplex-and-speech-interruption.md`: describes a real STT path.
- ADR-0007 (DDD): the engine is an infrastructure adapter behind a domain port.
- ADR-0014: the blackbox test must drive the public audio or transcript route. It must not patch the transcriber.
- Existing task TASK-0345 (proposed) decomposes `stt.py` by line count only. It does not change the default adapter. This task supersedes nothing. Run it first or coordinate the merge.

## Product & User Story References
- `docs/project/product/accepted/prd-0004-dynamic-vocal-audio-conditioning-and-dsp-filters.md`
- `docs/project/product/accepted/prd-0020-zero-latency-neural-voice-duplex-and-interruption.md`
- `docs/project/user_stories/accepted/us-0001-player-commands-board-via-voice.md`
- `docs/project/user_stories/accepted/us-0060-zero-latency-neural-voice-duplex.md`

## Detailed Specification & Implementation Plan
1. Define an `SpeechToText` port (Protocol) in `services/voice_agent/src/voice_agent/stt/port.py` (or the module chosen by TASK-0345). It takes PCM bytes and returns text, confidence, and an engine label.
2. Add `VoiceAgentSettings.stt_engine` (`faster-whisper` default; `mock` allowed only when a test sets it). Read it in `runefoble_platform.config` or the service settings module.
3. Build the adapter from settings in the composition root. Remove the module-level `MockWhisperTranscriber()` default.
4. When the engine fails to load or infer, raise a typed `SpeechEngineUnavailable` error. The chunk handler publishes an error event and sends no `PlayerSpokeEvent`.
5. Remove the `default_transcript` constant from production code. Move the mock to `tests/` fixtures.
6. Health endpoint reports the active STT engine name.
7. Update `docs/reference/ports-and-endpoints.md` and the voice how-to with the setting and the error behaviour.

## Frontdoor Blackbox Test Plan
- Before fix: POST a non-empty audio chunk through the public voice route with no `mock_transcript`. The response carries "I move 3 squares north" (test fails).
- After fix: same request with the engine forced unavailable through settings returns the error event and no `PlayerSpokeEvent` is published to the stream (test passes).
- After fix: with the test engine configured, the transcript returned equals the fixture transcript, and the health route names the engine.
- Tests use only HTTP and the Redis stream reader. They do not import the transcriber.

## Definition of Done
1. `default_transcript` and the mock default are gone from production modules. `rg "I move 3 squares north" services/voice_agent/src` returns nothing.
2. Port, production adapter, and error path implemented. Each file under 500 lines.
3. Blackbox tests above pass. `uv run pytest services/voice_agent` passes.
4. `uv run ruff check .` and `uv run ruff format --check .` pass.
5. Reference docs and the voice how-to updated. `CHANGELOG.md` `[Unreleased]` entry added.
