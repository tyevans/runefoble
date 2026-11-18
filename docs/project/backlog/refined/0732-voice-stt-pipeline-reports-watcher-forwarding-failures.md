---
id: '0732'
title: Voice STT Pipeline Reports Watcher Forwarding Failures Through a Port
status: Refined
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0015
governing_prds:
- PRD-0020
governing_stories:
- US-0060
target_bc: voice_agent
target_release: 0.9.0
---
# TASK-0732: Voice STT Pipeline Reports Watcher Forwarding Failures Through a Port

## Status
Refined. Found by the refactor audit round refactor-r1 and checked against the code on 2026-11-17.

## Summary
The STT pipeline logs a warning and returns no intent when it fails to reach The Watcher. The chunk result has no failure field. The client cannot tell that forwarding failed. The pipeline also builds a new HTTP client for each chunk.

## Problem Statement
- `services/voice_agent/src/voice_agent/stt.py:250-252`: `except Exception as e:` logs a warning and leaves `watcher_intent = None`.
- `stt.py:105` reads the Watcher URL from the environment inside the pipeline. `dependencies.py:20` reads the same variable.
- `stt.py:~224-251`: with no injected client, each chunk creates a new `httpx.AsyncClient`. Production never injects one.
- `process_chunk` is 115 lines. It mixes buffering, VAD, STT, publish, and forwarding.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0015.
- `docs/how-to/handle-neural-voice-duplex-and-speech-interruption.md`, `docs/reference/service-client.md`, `docs/how-to/test-cross-service-calls-with-live-upstreams.md`.
- TASK-0345 decomposes `stt.py`. Land the port first, or in the same pass.

## Product & User Story References
- PRD-0020
- US-0060

## Detailed Specification & Implementation Plan
1. Add `WatcherIntentPort.forward(payload, caller_authorization) -> IntentForwardResult` (typed: `intent` or `error`). Add one adapter built on the shared `ServiceClient`. Build it in the composition root and inject it into `StreamingAudioPipeline`.
2. Add `watcher_error: str | None` to `ChunkProcessingResult`. Set it when forwarding fails. Keep the transcript and `PlayerSpokeEvent`.
3. Remove the inline client and the second environment read. Move forwarding out of `process_chunk`.
4. Check `services/voice_agent/ui` and the gateway proxy for readers of the chunk response.

## Frontdoor Blackbox Test Plan
- Stream a chunk with The Watcher stopped (loopback upstream down). Assert the transcript and `PlayerSpokeEvent` are present, `watcher_error` is set, and no intent is returned.
- Stream a chunk with a live loopback Watcher. Assert the intent is returned.

## Definition of Done
- No `except Exception` that drops the forwarding error remains in `stt.py`.
- The reference doc for the chunk response lists `watcher_error`.
- `uv run pytest`, `make lint`, and `make health-check` pass. No file over 500 lines.
- Docs touched by the change are correct. `CHANGELOG.md` has an `[Unreleased]` entry.

## Audit Provenance
- Severity: medium
- Source audits: `watcher-voice-inference.md (F6)`
