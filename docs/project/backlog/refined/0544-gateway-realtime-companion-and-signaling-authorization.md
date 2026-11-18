---
id: '0544'
title: Gateway Realtime, Companion, and Signaling Authorization
status: Refined
created: 2026-11-17
dependencies:
- TASK-0520
- TASK-0541
- TASK-0542
- TASK-0521
- TASK-0522
governing_adrs:
- ADR-0001
- ADR-0006
- ADR-0014
governing_prds:
- PRD-0005
- PRD-0019
- PRD-0011
governing_stories:
- US-0014
- US-0006
- US-0059
- US-0030
target_release: 0.9.0
---

# TASK-0544: Gateway Realtime, Companion, and Signaling Authorization

## Status
Refined

## Summary
The gateway accepts WebSocket connections with no check. One session's broadcast reaches every session (`/ws/session/{id}`). Overlay and spectator sockets have no check. The companion router trusts a default identity header. The signaling layer takes identity from a query string or a raw bearer value. Per-message checks use names the schema does not define, and one fallback accepts a client-chosen action name. This task makes each socket subscribe through a schema permission, scopes broadcasts to that subscription, and removes client-chosen permission names.

## Problem Statement
- `gateway/api/src/gateway_api/main.py:102-117` (`/ws/session/{session_id}`): no authentication. Every message goes to every connection in every session (`ws_manager.broadcast`, line 116). Probe: a message from session A arrives on session B (`w3-authz-coverage.md` F6, `w1-gateway-api.md` F4).
- `gateway/api/src/gateway_api/routers/overlay.py:87-148` (`/ws/overlay/{id}`, `/overlay/ws/{id}`) and `routers/spectator.py:68-72`: no check. An unauthenticated overlay client can inject a `dice_rolled` event (`w3-authz-coverage.md` F6, `w1-gateway-api.md` F23).
- `gateway/api/src/gateway_api/websocket_endpoint.py:70-117`: the connect check uses `view` and `read`. `read` is not a campaign permission.
- `gateway/api/src/gateway_api/websocket_validator.py:47-111`: uses `campaign.read`, `campaign.edit`, `edit_character`, `move`, `move_token`, `participate`, `control`, `character.owner`, and the relations `dungeon_master` and `owner`. Line 111 falls back to `check_permission("campaign", id, action)` with the client-supplied action name (`w3-authz-coverage.md` F14).
- `gateway/api/src/gateway_api/signaling/auth.py:9-60`: identity from query, `x-user-id`, or the raw bearer value. A `guest_user` fallback exists at line 25. The checks use `campaign.owner`, `dungeon_master`, `player`, and `read` (`w3-authz-coverage.md` F14).
- `gateway/api/src/gateway_api/companion/router.py` (both POST routes): `x_user_id` defaults to `the_watcher_dm`. Omitting the header acts as that user (`w1-gateway-api.md` F22).
- `gateway/api/src/gateway_api/routers/tabletop.py:184-194` (`POST /api/v1/watcher/speak-and-act`): no check. The canned body is removed by the fake-implementation task. This task adds the check only.

## Documentation & Architecture Review
- ADR-0006 (Redis Streams): broadcasts carry domain events. A subscriber gets only the events for the streams it may observe.
- ADR-0001: a socket subscription is an object permission. Use `session.observe` for spectator-level reads and `session.participate` for player actions.
- `docs/how-to/authenticate-with-zitadel-oidc.md` and `docs/how-to/broadcast-obs-stream-overlay-and-cinematic-camera.md` describe sockets and overlay tokens. Update both.
- TASK-0508 (proposed, voice duplex routing and Zanzibar proxy) overlaps the signaling check. This task owns the gateway check. TASK-0508 owns the duplex routing.

## Product & User Story References
- US-0014 (realtime board WebSocket sync). US-0006 (spectator stream). US-0059 (companion haptic gateway). US-0030 (OBS overlay).

## Detailed Specification & Implementation Plan
1. Connect check. Every WebSocket route in this task runs after TASK-0522 verifies the principal. This task adds the permission check that follows:
   - Checks the object permission for the route. Session streams: `session.observe`. Campaign stream: `campaign.view`. Player-only channels: `session.participate`.
   - Closes with code 1008 (policy violation) on a missing principal or a denied check. Closes with 1011 on `AuthzUnavailableError`.
2. Scoped broadcast. `ws_manager` keys subscriptions by session id. A message goes only to subscriptions for that session. Replace the global broadcast in `main.py:116` with a session-scoped send.
3. Per-message checks in `websocket_validator.py`: map every action name through `ACTION_PERMISSIONS` (TASK-0542). Reject an unknown action with a protocol error. Delete the fallback at line 111 that passes a client-supplied name to `check_permission`.
4. Remove the `read`, `edit`, `move`, `move_token`, `participate`, `control`, `owner`, and `dungeon_master` names from the validator and from `signaling/auth.py`. Use the contract names.
5. `signaling/auth.py` and `companion/router.py`: identity replacement belongs to TASK-0522 (signaling) and TASK-0521 (companion). This task changes only the permission names and the checks in steps 3, 4, and 7.
6. `routers/overlay.py` and `routers/spectator.py`: overlay clients present an overlay token scoped to one session. Spectators need `session.observe`. Overlay tokens are issued by an authenticated route owned by the overlay task (not in this range). Until that route exists, the overlay socket accepts only spectator principals.
7. `POST /api/v1/watcher/speak-and-act`: require `session.participate` for the speaker. The speaker is the verified principal, not a body field.
8. Do not change the voice duplex routing (TASK-0508) or the minigame sockets (TASK-0548).

## Frontdoor Blackbox Test Plan
Setup: campaign and session created through the public routes; players join through invites (TASK-0543). Identities come from the verified-principal fixture.
- Before the fix, two unauthenticated sockets on sessions A and B: a message from A reaches B. After the fix, B receives nothing from A. The test uses `TestClient.websocket_connect`.
- A socket without a principal closes with 1008. Before the fix it is accepted.
- A spectator socket for a campaign it does not observe closes with 1008.
- A player sends an unknown action name. The server returns a protocol error. Before the fix the action is checked against a client-chosen name.
- `POST /api/v1/mobile/companion/{session_id}/turn-alert` without `x-user-id` and without a token returns 401. Before the fix it acts as `the_watcher_dm`.
- `POST /api/v1/watcher/speak-and-act` by a spectator returns 403.

## Definition of Done
1. The frontdoor tests above exist in `tests/test_blackbox_gateway_realtime_authz.py` and pass.
2. No gateway file in the change contains `guest_user`, `the_watcher_dm`, or a relation name in a `check_permission` call.
3. `/ws/session/{id}` broadcasts only inside one session. A test proves it.
4. `docs/how-to/broadcast-obs-stream-overlay-and-cinematic-camera.md` and `docs/how-to/authenticate-with-zitadel-oidc.md` describe the new rules.
5. `uv run pytest` passes for the changed gateway tests. `uv run ruff check gateway/api` passes.
6. No file in the change exceeds 500 lines. Split `websocket_validator.py` or `signaling/auth.py` if needed.

## Audit Provenance

- Severity: critical
- Source audits: `w3-authz-coverage.md`, `w1-gateway-api.md`
