---
id: '0850'
title: Voice Audio Parser Rejects Malformed WAV Instead of Guessing the Audio
status: Complete
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: voice_agent
target_release: 0.9.0
---
# TASK-0850: Voice Audio Parser Rejects Malformed WAV Instead of Guessing the Audio

## Status
Complete

## Summary
`parse_audio_data` in the voice agent returns raw bytes after a fixed 44-byte header when a RIFF file has no `data` chunk. It also catches every exception and returns the same guess. A malformed file becomes noise, and nothing is logged. The fix raises a typed `AudioFormatError`, removes the broad `except`, and maps the error to a 400 response at the edge.

## Problem Statement
- `services/voice_agent/src/voice_agent/vad.py:26`: a RIFF file without a `data` chunk returns `data_bytes[44:]` with no error and no log.
- `vad.py:27-28`: `except Exception` returns `data_bytes[44:]` with the default sample rate. The loop bounds make `struct.error` unlikely, so the handler mostly hides logic errors.

## Documentation & Architecture Review
- ADR-0015 Context item 4: a failed dependency must not look like a working one. Bad input follows the same rule.
- `docs/how-to/manage-spoken-reactions-and-ready-actions.md` and `docs/reference/ports-and-endpoints.md`: check the transcribe route and the audio WebSocket for the error shape.
- TASK-0345 (proposed) decomposes `stt.py` and touches the same caller. Run this task before TASK-0345.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Add `AudioFormatError(ValueError)` in the voice agent package. Raise it when a RIFF header is shorter than 44 bytes, or when the chunk walk ends without a `data` chunk.
2. Remove the `try` and `except Exception` around the chunk walk.
3. Find the callers of `parse_audio_data` (`grep` in `services/voice_agent/src`). The HTTP transcribe route maps `AudioFormatError` to 400 with a stable error code. The WebSocket path sends a typed error frame and does not forward a chunk.
4. Keep the output for valid PCM and valid WAV unchanged.

## Frontdoor Blackbox Test Plan
- POST a RIFF body with no `data` chunk to the public transcribe route. Assert 400 and the stable error code. Assert no Watcher call happened.
- POST a valid WAV file. Assert the same transcript as before the change.
- Send a malformed frame on the audio WebSocket. Assert a typed error frame.

## Definition of Done
- `vad.py` has no broad `except` and no guessed header path.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `refactor-r2/services-backend.md` (F3)
