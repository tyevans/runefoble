---
id: '0833'
title: "Voice Agent Supports a whisper.cpp HTTP Speech Engine"
status: Complete
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0015
governing_prds:
- PRD-0001
governing_stories: []
target_bc: voice_agent
target_release: 0.9.0
---

# TASK-0833: Voice Agent Supports a whisper.cpp HTTP Speech Engine

## Status
Complete

## Summary
The voice agent supports only the in-process faster-whisper engine. The user runs a whisper.cpp server on the local network and wants the voice agent to use it, so the pod needs no model cache.

## Problem Statement
- `services/voice_agent/src/voice_agent/speech_settings.py:23`: `stt_engine: Literal["faster-whisper"]`.
- A whisper.cpp server takes `POST /inference` (multipart audio file; fields such as `response_format=json`, `temperature`) and returns the transcript.

## Documentation & Architecture Review
- `docs/how-to/add-an-engine-port-adapter.md`: a settings-selected adapter; an unavailable engine returns 503 and never substitute output.
- `docs/how-to/handle-neural-voice-duplex-and-speech-interruption.md`.

## Product & User Story References
PRD-0001 (speak and the board obeys: speech is parsed into board actions).

## Detailed Specification & Implementation Plan
1. Add engine `whisper-cpp` to `stt_engine`, with `RUNEFOBLE_VOICE_STT_BASE_URL` (no default) and a request timeout.
2. The adapter posts each buffered utterance as WAV to `{base_url}/inference` and maps the reply to the transcriber result. A connection error or non-2xx answer is a 503 (engine unavailable). Health reports the engine as not ready when the server does not answer.
3. Helm: values for the engine and base URL; with `whisper-cpp`, no model cache volume is needed. Add the keys to `values.local.example.yaml`.
4. Document the engine in the how-to and `docs/reference/`.

## Frontdoor Blackbox Test Plan
- A local loopback HTTP server that acts as whisper.cpp (`tests/helpers/local_http_server.py`): the transcribe route returns its transcript.
- The server answers 500 or is down: the route answers 503 and `/healthz` reports not ready.
- An unknown engine name still stops start-up.

## Definition of Done
- The test plan passes. `make test`, `make lint` and `make health-check` pass.

## Audit Provenance
- Severity: feature (user request, 2026-11-18)
- Source audits: user message naming the whisper.cpp server on the local network
