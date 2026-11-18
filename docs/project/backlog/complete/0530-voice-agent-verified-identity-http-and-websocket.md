---
id: '0530'
title: Voice Agent Verifies Identity on HTTP and WebSocket Routes
status: Complete
created: 2026-11-17
dependencies:
- TASK-0520
- TASK-0522
- TASK-0536
governing_adrs:
- ADR-0001
- ADR-0005
- ADR-0007
governing_prds:
- PRD-0004
- PRD-0019
- PRD-0020
governing_stories:
- US-0013
target_release: 0.9.0
---

# TASK-0530: Voice Agent Verifies Identity on HTTP and WebSocket Routes

## Status
Complete

## Summary
The voice service takes the subject of a request from `X-User-Id`, the raw bearer text, a query parameter, or a default value such as `guest_user` or `dm_user`. The SpiceDB checks then run on that subject. Apply the verified principal to every voice route, and make the WebSocket routes authenticate before accept.

## Problem Statement
- `services/voice_agent/src/voice_agent/room_routes.py:23-34` (`extract_user_id`) reads `X-User-Id`, then the raw `Authorization` value, then `?user_id=` or `?token=`, then `guest_user`. The kick endpoint (lines 45-70) uses that subject for SpiceDB. Audit w2-voice-agent F3.
- `routers/vocal_effects.py:49-55` (`_extract_user_id`) uses the same order with default `dm_user`. The modulate endpoint uses it for authorization.
- No JWT check exists anywhere in `services/voice_agent/src`. Audit w2-voice-agent F3.
- `routers/duplex.py:77` (`/api/v1/voice/duplex/ws`) and `stream_routes.py:81` (`/api/v1/voice/stream/ws`) have no authentication. Audit w3-authz F14.
- Many voice POST routes (`synthesis.py`, `audio.py`, `stream_diagnostics.py`, `aec_diagnostics.py`, `audio_filters.py`, `duplex.py:25`, `stream_routes.py:49`) take no identity at all. Audit w3-authz route table rows 288-305.

## Documentation & Architecture Review
- TASK-0508 (proposed) covers gateway voice duplex routing and the Zanzibar proxy. It does not name JWT verification (audit w2-voice-agent F3). Keep it separate. The gateway side is TASK-0522.
- The service verifies the token itself (same pattern as TASK-0527). The gateway forwards it (TASK-0536).
- Relation names used in `room_routes.py:63-64` (`campaign#owner`, `campaign#dungeon_master`) are an authorization defect. Out of scope here.

## Product & User Story References
- PRD-0004 (voice DSP), PRD-0019 (companion and haptics), PRD-0020 (voice duplex). US-0013.

## Detailed Specification & Implementation Plan
1. Add the issuer, audience, and JWKS settings to the voice service.
2. Delete `extract_user_id` and `_extract_user_id`. Use `require_principal` (HTTP) on all routers through `APIRouter(dependencies=[...])`.
3. WebSocket routes (`duplex.py`, `stream_routes.py`) call `authenticate_websocket` from TASK-0520 before accept. Use the subprotocol contract. Reject the handshake on failure.
4. Delete the query-string, header, and default-subject branches everywhere in the service. Confirm with `grep -rn "guest_user\|dm_user\|X-User-Id\|user_id=" services/voice_agent/src`.
5. Keep health and manifest routes public.
6. Helm: add the three issuer variables to the voice template.

## Frontdoor Blackbox Test Plan
HTTP and WebSocket tests against the voice app with signing-issuer tokens.
- Before: `POST /api/v1/voice/rooms/{id}/kick` with `?user_id=dm` and no bearer returns a result. `/api/v1/voice/duplex/ws` accepts any connection.
- After:
  - Every mutating HTTP route returns 401 with no bearer, garbage bearer, or forged token.
  - A forged `X-User-Id` header does not change the subject. The kick request uses the token subject.
  - WebSocket handshake is denied without a valid protocol token, and accepted with one.

## Definition of Done
1. Grep in step 4 returns no production matches.
2. Voice service suites pass with the signing issuer.
3. Helm renders the variables.
4. `docs/how-to` pages for voice (`handle-neural-voice-duplex-and-speech-interruption.md`, `connect-mobile-companion-and-haptic-gateway.md`) show the bearer and subprotocol contract.
5. No file exceeds 500 lines.

## Audit Provenance

- Severity: critical
- Source audits: `w2-voice-agent.md`, `w3-authz-coverage.md`
