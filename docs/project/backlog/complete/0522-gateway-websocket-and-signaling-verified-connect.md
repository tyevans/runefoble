---
id: '0522'
title: Gateway WebSocket and Signaling Connections Authenticate Before Accept
status: Complete
created: 2026-11-17
dependencies:
- TASK-0520
governing_adrs:
- ADR-0001
- ADR-0005
- ADR-0013
governing_prds:
- PRD-0023
- PRD-0020
governing_stories:
- US-0013
target_release: 0.9.0
---

# TASK-0522: Gateway WebSocket and Signaling Connections Authenticate Before Accept

## Status
Complete

## Summary
Require a verified principal on every gateway WebSocket and signaling route before the handshake completes. Remove the query-string and header identity, the `?user_id=` impersonation, and the `guest_user` fallback. Per-message authorization and session-scoped broadcast belong to the authorization theme.

## Problem Statement
- `gateway/api/src/gateway_api/main.py:102-117` (`/ws/session/{session_id}`) has no authentication. Every frame goes to every socket. Audit w3-authz F6, w1-gateway-api F4.
- `gateway/api/src/gateway_api/routers/overlay.py:87-148` (`/ws/overlay/{id}` and `/overlay/ws/{id}`) and `routers/spectator.py:68-72` have no authentication.
- `gateway/api/src/gateway_api/websocket_auth.py:59-60` takes `?user_id=` as identity (impersonation). `extract_subject_id` also reads `x-user-id` and the raw bearer text.
- `gateway/api/src/gateway_api/signaling/auth.py:8-27` takes identity from the query string, `x-user-id`, or the raw bearer value, and falls back to `guest_user` (line 25). Audit w2-voice-agent F3.
- `gateway/api/src/gateway_api/websocket_endpoint.py:70-117` (campaign socket) accepts `?user_id=` dev impersonation. Audit w3-authz route table row 9.
- `main.py:122-146` (voice, mobile companion, establishment table, and minigame sockets) use the same identity sources. `main.py:134,146` hardcode `est-default`.

## Documentation & Architecture Review
- TASK-0520 provides `authenticate_websocket` and the subprotocol contract (`runefoble.v1` plus `runefoble.bearer.<jwt>`). Use it. Do not add a second handshake check.
- TASK-0508 (proposed) covers voice duplex routing and the Zanzibar proxy. It does not cover identity. This task does not supersede it. Both must agree on the connect contract.
- Clients change in TASK-0538.

## Product & User Story References
- US-0013 (gateway authorization) and PRD-0023 (signed-in sessions).
- PRD-0020 for voice sockets. Its latency target is unchanged. The handshake check adds one token verification per connection.

## Detailed Specification & Implementation Plan
1. Use `authenticate_websocket` from TASK-0520 in every gateway WebSocket handler. Call it before `accept`. On failure, reject the handshake and log only the failure reason, not the token.
2. Routes to change (all of them):
   - `/ws/campaigns/{campaign_id}` (`websocket_endpoint.py`)
   - `/ws/session/{session_id}` (`main.py`)
   - `/ws/voice/{session_id}` and `/ws/mobile-companion/{session_id}` (`signaling/endpoint.py`, `companion/endpoint.py`)
   - `/ws/establishments/{establishment_id}/tables/{table_id}` and `/ws/minigames/{table_id}` (`main.py`)
   - `/overlay/ws/{session_id}` and `/ws/overlay/{session_id}` (`routers/overlay.py`)
   - `/ws/spectator/{session_id}` (`routers/spectator.py`)
3. Delete `extract_subject_id`, the `?user_id=` branch, the `x-user-id` branch, the raw-bearer branch, and `guest_user`. Keep one code path.
4. `signaling/auth.py` keeps the SpiceDB calls but takes the subject from the principal. Relation names used there belong to the authorization theme.
5. The `est-default` hardcoded establishment in `main.py` is kept as a route value only. Do not use it as an identity or a permission shortcut.
6. Out of scope (authorization theme): per-message checks, `player_id` taken from the payload, and broadcast scoped to a session.

## Frontdoor Blackbox Test Plan
New file `tests/test_blackbox_gateway_ws_identity.py`, using the WebSocket test client.
- Before: connect to `/ws/session/abc` with no token succeeds. Connect to `/ws/campaigns/c1?user_id=someone` succeeds.
- After:
  - No token, garbage token, and forged HS256 token: handshake denied. No frame is delivered.
  - Query-string `user_id` and `x-user-id` header alone: handshake denied.
  - Valid token offered as `runefoble.bearer.<jwt>`: handshake accepted with subprotocol `runefoble.v1`.
  - The same check applies to all eight route groups listed in step 2 (parameterised test).

## Definition of Done
1. Every WebSocket route in `gateway/api` calls `authenticate_websocket` before accept. Verify with `grep -rn "websocket(" gateway/api/src` and a per-route test.
2. `grep -rn "guest_user\|user_id=\|x-user-id" gateway/api/src` returns no identity use.
3. `uv run pytest tests/test_blackbox_gateway_ws_identity.py` passes. Existing WebSocket suites pass with the signing issuer.
4. `uv run ruff check gateway/api` passes. No file exceeds 500 lines.
5. Integrated after TASK-0520. TASK-0538 updates the clients in the same release.

## Audit Provenance

- Severity: critical
- Source audits: `w3-authz-coverage.md`, `w1-gateway-api.md`, `w2-voice-agent.md`
