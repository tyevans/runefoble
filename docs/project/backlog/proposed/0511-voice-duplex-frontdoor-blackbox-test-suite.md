---
id: '0511'
title: Voice Duplex Frontdoor Blackbox Test Suite
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0508
- TASK-0509
- TASK-0510
governing_adrs:
- ADR-0001
- ADR-0002
- ADR-0014
governing_prds:
- PRD-0020
governing_stories:
- US-0023
- US-0060
target_release: 0.9.0
---

# TASK-0511: Voice Duplex Frontdoor Blackbox Test Suite

## Status
Proposed

## Summary
Implement a comprehensive frontdoor blackbox test suite (`tests/test_blackbox_voice_duplex_gateway.py` and `frontend/test/voice-duplex-app-shell.test.ts`) validating end-to-end voice duplex communication through Gateway public frontdoors: verifying SpiceDB Zanzibar authorization checks on `/ws/voice/duplex/{session_id}`, simulating incoming speech audio frames to assert sub-80ms barge-in detection, validating `VoiceSpeechInterrupted` CloudEvent emission, and testing App Shell HUD visual feedback per ADR-0014 and PRD-0020.

## Problem Statement
While unit tests exist for isolated DSP filters (`tests/test_blackbox_voice_duplex.py`), there is no end-to-end blackbox test verifying the complete user journey across Gateway proxying, SpiceDB Zanzibar access control, Redis Streams event bus propagation, Watcher narration cancellation, and frontend DOM updates. Without this suite, regressions in WebSocket framing, auth token parsing, or event schemas cannot be caught before deployment.

## Governing Architecture & ADRs
- **ADR-0001: Google Zanzibar for Fine-Grained Authorization**: Verifying 403 Forbidden rejection when unauthorized users attempt to open duplex streams.
- **ADR-0002: Event-Driven Watcher Gameplay Orchestration**: Verifying asynchronous event propagation and reaction timing.
- **ADR-0014: Blackbox Frontdoor Testing & BDD Governance**: Ensuring tests interact strictly through public HTTP routes, WebSockets, and emitted CloudEvents without database backdoors.

## Product & User Story References
- [`prd-0020-zero-latency-neural-voice-duplex-and-interruption.md`](../../product/accepted/prd-0020-zero-latency-neural-voice-duplex-and-interruption.md)
- [`us-0023-spoken-reaction-interrupts-and-ready-actions.md`](../../user_stories/accepted/us-0023-spoken-reaction-interrupts-and-ready-actions.md)
- [`us-0060-zero-latency-neural-voice-duplex.md`](../../user_stories/accepted/us-0060-zero-latency-neural-voice-duplex.md)

## Scope of Work
1. **Gateway Voice Duplex Blackbox Test (`tests/test_blackbox_voice_duplex_gateway.py`)**:
   - Establish WebSocket connection to `/ws/voice/duplex/{session_id}` with valid JWT credentials.
   - Assert connection failure (close code 4403) when user lacks session membership.
   - Send active narration playback command followed by synthetic speech PCM frames.
   - Assert receipt of `barge_in_detected` WebSocket frame within < 100ms.
   - Validate `VoiceSpeechInterrupted` CloudEvent payload published to Redis Streams.
   - Assert `GET /api/v1/voice/duplex/stats` accurately reflects interruption event and latency.
2. **Frontend App Shell Voice Duplex Test (`frontend/test/voice-duplex-app-shell.test.ts`)**:
   - Mount `<runefoble-voice-duplex-controls>` within test container.
   - Dispatch simulated `barge_in_detected` event.
   - Assert DOM reflects `"BARGE-IN DETECTED"` banner and dispatches `duplex-interrupted` custom event.

## Definition of Done
1. `uv run pytest tests/test_blackbox_voice_duplex_gateway.py` passes 100% cleanly.
2. `pnpm test frontend/test/voice-duplex-app-shell.test.ts` executes and passes.
3. Tests strictly exercise public Gateway endpoints and WebSockets with zero backdoor mocking.
