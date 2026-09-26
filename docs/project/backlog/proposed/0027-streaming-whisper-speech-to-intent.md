---
id: 0027
title: Sub-500ms Streaming Audio Whisper Transcription & VAD Pipeline
status: Proposed
created: 2026-09-25
dependencies: [TASK-0002, TASK-0025]
governing_adrs: [ADR-0002, ADR-0006]
target_release: 0.2.0
---

# TASK-0027: Sub-500ms Streaming Audio Whisper Transcription & VAD Pipeline

## Status
Proposed

## Summary
Connect live audio streams from WebRTC voice rooms (`TASK-0025`) into a real-time Voice Activity Detection (VAD) and Whisper acoustic inference pipeline in `services/voice_agent`, streaming incremental transcripts to `services/the_watcher` within a sub-500ms end-to-end latency budget.

## Problem Statement
The Runefoble design principle states: "Speak and the board obeys: natural speech is parsed into game actions within 500ms without blocking audio pipelines." Currently, `voice_agent` provides a simulated/batch `/api/v1/voice/transcribe` HTTP endpoint. For live gameplay, continuous Opus/PCM audio chunks must be segmented using Silero VAD, transcribed via Whisper (or faster-whisper/Whisper.cpp), and pushed into the speech-to-intent pipeline immediately upon utterance completion.

## Proposed Scope
1. **Streaming Audio Buffer & VAD Segmenter**:
   - Continuous audio buffer per active speaker in `services/voice_agent`.
   - VAD chunking detecting speech onsets and silence boundaries (< 250ms silence detection).
2. **Whisper Transcription Worker**:
   - Integration with Whisper streaming inference backend.
   - Fallback and mock transcription modes for CI/local developer environments.
3. **Intent Streaming Dispatch**:
   - Direct pub/sub dispatch to `runefoble.events.session` emitting `PlayerSpokeEvent` and forwarding to `the_watcher` intent parsing.
4. **Latency Budget & Metrics**:
   - OpenTelemetry metrics measuring VAD duration, transcription latency, intent parsing, and board mutation.

## Acceptance Criteria
1. End-to-end latency from utterance conclusion to `SpeechIntentParsed` event under 500ms.
2. Robust blackbox integration tests validating streamed audio chunks against public audio ingestion endpoints.
3. Clean error handling when audio streams suffer packet loss or disconnection.
