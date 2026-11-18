---
id: '0558'
title: Voice Agent Verified Identity, Session Checks, and Diagnostics Authorization
status: Complete
created: 2026-11-17
dependencies:
- TASK-0520
- TASK-0541
- TASK-0542
- TASK-0540
- TASK-0530
governing_adrs:
- ADR-0001
- ADR-0006
- ADR-0007
- ADR-0014
governing_prds:
- PRD-0020
- PRD-0004
governing_stories:
- US-0060
- US-0011
- US-0020
- US-0001
target_release: 0.9.0
---

# TASK-0558: Voice Agent Verified Identity, Session Checks, and Diagnostics Authorization

## Status
Complete

## Summary
The voice agent takes identity from `X-User-Id`, from a raw bearer value, from a query string, or from a default. The kick route and the vocal modulation route then pass that identity to SpiceDB, so a caller who names another user passes the check for that user. Public audio, synthesis, transcription, and diagnostics routes have no check. SpiceDB transport errors escape as unhandled exceptions. This task makes every voice route use the verified principal, binds each route to a schema permission, and maps SpiceDB failures to 503.

## Problem Statement
- `services/voice_agent/src/voice_agent/room_routes.py:23-34` (`extract_user_id`): `X-User-Id`, then the raw `Authorization` value, then `?user_id=` or `?token=`, then `guest_user`. The kick route (`:45-70`) passes this value to SpiceDB (`w2-voice-agent.md` F3).
- `services/voice_agent/src/voice_agent/routers/vocal_effects.py:49-55` (`_extract_user_id`): same pattern with default `dm_user`. Used for `POST /api/v1/voice/modulate` (`:76`) authorization (`w2-voice-agent.md` F3).
- No voice route validates a JWT (`w2-voice-agent.md` F3).
- Routes with no check (`w3-authz-coverage.md` rows 288-301, 304-306): `routers/aec_diagnostics.py:49`, `routers/audio.py:16`, `routers/audio_filters.py:51`, `routers/duplex.py:25` and the duplex WebSocket at `:77`, `routers/stream_diagnostics.py:75`, `routers/synthesis.py:42,88`, `stream_routes.py:49` and the stream WebSocket at `:81`.
- `room_routes.py` and `vocal_effects.py`: a SpiceDB transport error propagates as `grpc._channel._InactiveRpcError`, returned as an unhandled 500 (`w2-voice-agent.md` F14).
- Gateway signaling (`gateway/api/src/gateway_api/signaling/auth.py`) uses the same identity order. TASK-0544 changes the gateway side.
- Not in this task: `mock_transcript` on the public stream schema (`w2-voice-agent.md` F2). That is a test backdoor and belongs to the fake-implementation and test-backdoor work. It is recorded in the index.

## Documentation & Architecture Review
- ADR-0001: kick and room control check `session.control`. Modulation and speech input check `session.participate` for the speaker. Diagnostics and benchmarks check `campaign.run_session` on the campaign of the session in the request. Synthesis checks `session.participate`.
- ADR-0006 (Redis Streams): the voice event flow stays on the bus. Authorization happens on the HTTP and WebSocket frontdoor.
- ADR-0014: tests use the public voice routes and the gateway. The duplex and stream tests use real WebSocket connections.
- `docs/how-to/handle-neural-voice-duplex-and-speech-interruption.md`, `docs/how-to/modulate-dm-vocal-npc-presets.md`, and `docs/how-to/manage-spoken-reactions-and-ready-actions.md` describe these routes. Update the auth text.
- TASK-0508 (proposed) covers the gateway duplex routing and the Zanzibar proxy. This task owns the voice service checks. TASK-0508 owns the gateway route. Record the boundary in the index.

## Product & User Story References
- US-0060 (zero-latency neural voice duplex). US-0011 (dynamic voice filters). US-0020 (DM vocal modulator). US-0001 (player commands the board by voice). PRD-0020 (voice duplex). PRD-0004 (DSP filters).

## Detailed Specification & Implementation Plan
1. Identity: TASK-0530 replaces every identity source with the verified principal. This task uses that principal for the checks in step 2. Confirm that TASK-0530 removed `extract_user_id`, `_extract_user_id`, `guest_user`, and `dm_user`.
2. Permission per route:
   - Kick (`room_routes.py:45`): `session.control`. Remove the two relation checks (`owner` and `dungeon_master` on campaign).
   - Modulate (`vocal_effects.py:76`): `session.participate`.
   - DSP apply, barge-in evaluate, playback start, synthesis, transcription, stream chunk, duplex and stream WebSockets: `session.participate` for the speaker id that the request names. The speaker id must equal the principal, or the principal holds `session.control`.
   - AEC benchmark, stream diagnostics report and quality: `campaign.run_session` on the campaign of the session in the request.
3. SpiceDB errors: map `AuthzUnavailableError` to 503 with a stable body `{"error": "authorization_unavailable"}`. Map `AuthzSchemaError` to 500 with an error id. Never return the raw gRPC error to the caller.
4. Remove the module-level state that only holds identity, if it exists (`w2-voice-agent.md` F12 covers the playback state; that part is out of this task).
5. Delete the local SpiceDB factory and import the library factory.

## Frontdoor Blackbox Test Plan
Setup: a campaign, a session, a DM, and a player. Rooms and sessions are created through the public voice and session routes. Roles come from TASK-0543.
- Before the fix, `POST /api/v1/voice/rooms/{id}/kick` with `X-User-Id` set to the DM returns 200 from a player call. After the fix a player gets 403 and the DM gets 200, and the identity is the principal only.
- A kick with a raw bearer value as identity: 401. Before the fix the raw value is accepted as a user id.
- `POST /api/v1/voice/aec/benchmark` with no principal: 401. Before the fix it returns 200.
- `POST /api/v1/voice/synthesize` by a spectator: 403.
- Duplex WebSocket connect without a principal: refused. A connect for another speaker id: refused.
- With a stubbed SpiceDB outage, kick returns 503 with the stable body. Before the fix it returns 500 with a traceback.

## Definition of Done
1. Frontdoor tests exist in `tests/test_blackbox_voice_authz.py` and pass against the live harness.
2. No `X-User-Id`, `guest_user`, `dm_user`, or query-string identity read remains in `services/voice_agent/src/voice_agent`.
3. Every route listed in the Problem Statement has one permission call.
4. The voice how-to docs listed above are updated.
5. `uv run pytest services/voice_agent` passes. `uv run ruff check services/voice_agent` passes.
6. No file in the change exceeds 500 lines.

## Audit Provenance

- Severity: critical
- Source audits: `w2-voice-agent.md`, `w3-authz-coverage.md`
