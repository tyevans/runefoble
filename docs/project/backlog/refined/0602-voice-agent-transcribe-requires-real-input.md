---
id: '0602'
title: Voice Agent Transcribe Route Requires Real Audio or Transcript
status: Refined
created: 2026-11-17
dependencies:
- TASK-0600
governing_adrs:
- ADR-0002
- ADR-0014
governing_prds:
- PRD-0020
governing_stories:
- US-0001
- US-0060
target_release: 0.9.0
severity: high
source_audits:
- w2-voice-agent.md
---

# TASK-0602: Voice Agent Transcribe Route Requires Real Audio or Transcript

## Status
Refined

## Summary
The transcribe route invents a player action when the request has no text. `audio_base64` is accepted but never decoded. This task makes the route decode audio through the STT port (TASK-0600) and return 422 when neither input is present. The route never invents text.

## Problem Statement
- `services/voice_agent/src/voice_agent/routers/synthesis.py:90`: `transcript = req.transcript or "I inspect my surroundings."`.
- `TranscribeRequest.audio_base64` (`models.py`) is never read.
- The invented transcript is published as `PlayerSpokeEvent` (`synthesis.py` near lines 95-107) and sent to The Watcher. A real player action is created from nothing.

Source: `.audit/reports/w2-voice-agent.md` F5.

## Documentation & Architecture Review
- `docs/reference/events-schema.md`: `PlayerSpokeEvent` must carry a transcript that came from the speaker's audio or from text the client typed. Update the schema text if it says otherwise.
- ADR-0002: The Watcher consumes events. It must not receive invented player events.
- ADR-0014: test through the public route only.

## Product & User Story References
- `docs/project/user_stories/accepted/us-0001-player-commands-board-via-voice.md`
- `docs/project/product/accepted/prd-0020-zero-latency-neural-voice-duplex-and-interruption.md`

## Detailed Specification & Implementation Plan
1. In the transcribe handler, if `transcript` is empty and `audio_base64` is absent, return 422 with a clear message.
2. If `audio_base64` is present, base64-decode it and call the STT port from TASK-0600. Use the returned text.
3. If `transcript` is present, use it as typed text and label the source `client_text`.
4. Publish `PlayerSpokeEvent` only when the text came from step 2 or 3. Never publish fallback text.
5. Include the source label in the response.

## Frontdoor Blackbox Test Plan
- Before fix: POST `{}` to the transcribe route. Response 200 with "I inspect my surroundings." and a published event (test fails).
- After fix: POST `{}` returns 422 and publishes no event on the stream.
- After fix: POST with `audio_base64` (test engine fixture) returns the fixture transcript and source `audio`.
- After fix: POST with `transcript` returns source `client_text`.

## Definition of Done
1. The string "I inspect my surroundings." is removed from `services/voice_agent`.
2. `audio_base64` is decoded and used.
3. Blackbox tests pass. Pytest for `services/voice_agent` passes.
4. Ruff check and format pass.
5. Events schema and voice how-to updated where they describe this route.
