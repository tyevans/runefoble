---
id: 0039
title: Sub-500ms Streaming Audio Whisper Transcription & VAD Pipeline
status: Complete
created: 2026-09-25
dependencies:
- TASK-0002
- TASK-0033
governing_adrs:
- ADR-0002
- ADR-0006
- ADR-0007
target_release: 0.2.0
pr_url: https://github.com/tyevans/runefoble/pull/22
---
# TASK-0039: Sub-500ms Streaming Audio Whisper Transcription & VAD Pipeline

## Status
Refined

## Summary
Connect live audio streams from WebRTC voice rooms into a real-time Voice Activity Detection (VAD) and Whisper acoustic inference pipeline in `services/voice_agent`, streaming incremental transcripts to `services/the_watcher` within a sub-500ms end-to-end latency budget to fulfill the platform design principle: "Speak and the board obeys".

## Problem Statement
The Runefoble design principle requires natural speech to be parsed into game actions within 500ms without blocking audio pipelines. While `voice_agent` currently provides a batch transcription endpoint, live gameplay demands continuous Opus/PCM audio streaming, Silero VAD segmentation (< 250ms silence threshold), streaming Whisper transcription, and immediate event publication onto Redis Streams.

## INVEST Criteria Evaluation
- **Independent (I)**: Consumes WebRTC audio streams or raw PCM audio chunks via public voice agent endpoints; publishes standardized `PlayerSpoke` events consumed by `the_watcher`.
- **Negotiable (N)**: Acoustic model sizes (tiny.en, base.en, or local faster-whisper backend), VAD sensitivity thresholds, and batch chunk intervals are configurable.
- **Valuable (V)**: Fulfills the core system promise of instantaneous voice-driven tabletop gameplay with sub-500ms voice-to-board latency.
- **Estimable (E)**: Proven combination of Silero VAD, faster-whisper CTranslate2 runtime, and Redis Streams pub/sub.
- **Small (S)**: Scope strictly isolated to `services/voice_agent/src/voice_agent/stt.py`, streaming endpoint handlers, and latency measurement helpers.
- **Testable (T)**: Frontdoor blackbox tests streaming synthesized PCM audio chunks through public HTTP/WebSocket voice endpoints and asserting `PlayerSpoke` and `SpeechIntentParsed` events arrive on Redis Streams within SLA.

## Governing Architecture & ADRs
- **ADR-0002**: Realtime Voice Streaming and Audio Pipeline Architecture.
- **ADR-0006**: Redis Streams Event Streaming.
- **ADR-0007**: Domain-Driven Design Architecture.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Streaming Audio Buffer & VAD Segmenter (`services/voice_agent/src/voice_agent/stt.py`)**:
   - Ring buffer for live audio frames per participant.
   - VAD segmentation detecting utterance completion with < 250ms silence detection.
2. **Streaming Whisper Ingestion Endpoint (`POST /api/v1/voice/stream/chunk`)**:
   - Ingests PCM/WAV chunks, processes VAD boundaries, triggers transcription, and dispatches `PlayerSpoke` CloudEvent to Redis Streams.
   - Includes mock transcription provider for deterministic offline and CI test execution.
3. **Blackbox TDD Suite (`tests/test_blackbox_streaming_whisper.py`)**:
   - Stream audio buffers through public HTTP/WebSocket frontdoor and assert event bus receives valid `PlayerSpoke` event with transcribed intent within latency bounds.
4. **Diataxis Documentation**:
   - Update `docs/explanation/realtime-voice-and-board-sync.md` with streaming VAD pipeline architecture.
5. **File Invariant Check**:
   - All touched files remain strictly under 500 lines.
