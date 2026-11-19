---
id: '0910'
title: The Session Socket Relays No Forged Server Frames, and Launch Calls the Start Route
status: Complete
created: 2026-11-19
dependencies: []
governing_adrs:
- ADR-0001
- ADR-0011
- ADR-0013
- ADR-0014
- ADR-0015
governing_prds:
- PRD-0023
governing_stories:
- US-0065
- US-0017
target_bc: gateway_api
target_release: 0.9.0
---
# TASK-0910: The Session Socket Relays No Forged Server Frames, and Launch Calls the Start Route

## Status
Complete

## Summary
Any session participant can send a `session_started` frame on the session socket. The gateway relays it to every observer, and each App Shell then moves to the route that the frame names. The session stays in `lobby`, because the App Shell "Launch Session" button never calls `POST /api/v1/sessions/{id}/start`. The same inbound allow-list also lets a participant forge `turn_advanced`, `dice_rolled`, `token_moved` and `dm_whisper` frames. No server code sends these kinds on the session socket, so the only source of them is a client.

## Problem Statement
- `gateway/api/src/gateway_api/session_frames.py:16-30`: `SESSION_FRAME_KINDS` is the inbound allow-list. It contains `session_started`, `turn_advanced`, `dice_rolled`, `token_moved` and `dm_whisper`.
- `gateway/api/src/gateway_api/session_websocket.py:36-44`: `relay` validates the kind, calls `may_publish_frame`, then broadcasts the client payload unchanged to every socket in the session.
- `gateway/api/src/gateway_api/session_access.py:37-61`: `may_publish_frame` checks only `session.participate` for every kind. In `libs/runefoble_auth/schema/runefoble.zed:42-44`, `participate = campaign->play`. Every campaign player has it. The check does not depend on the frame kind.
- `frontend/src/app/session-socket.ts:109-110`: on `session_started`, the App Shell navigates to `#/campaigns/${msg.campaignId}/sessions/${msg.sessionId}`. The ids come from the frame. A forged frame moves every observer to a route that the sender chooses. The handler does not read `status`.
- `frontend/src/app/session-actions.ts:15-25`: `launchSession` sends `{type: 'session_started', ...}` on the socket and navigates. It never calls the start route. US-0065 Scenario 2 says that launch invokes `POST /api/v1/sessions/15/start` and moves the session from `lobby` to `active`. The App Shell does not do this.
- `gateway/api/src/gateway_api/routers/sessions_proxy.py:65-78`: the gateway start route broadcasts `session_started` after the owner replies. It reads `state["status"]`. An owner reply without `status` raises `KeyError` and gives 500. This is the only legitimate source of the frame.
- `grep` of `gateway/`, `services/*/src` and `libs/` finds no server code that sends `turn_advanced`, `dice_rolled`, `token_moved` or `dm_whisper` on the session socket. `frontend/src/vtt-mesh-handlers.ts:23-29` dispatches them as window events, so a forged `dm_whisper` reaches the whisper bar of every connected browser, players included.

## Documentation & Architecture Review
- ADR-0001: object permissions come from `runefoble.zed`. A DM-only frame needs `session.control`, not `session.participate`.
- ADR-0015 (b): the gateway is thin and holds no state. Hard Invariant 2: state changes come from the owner. The lobby-to-active move belongs to game_session.
- TASK-0810 (complete) added the inbound allow-list and the `participate` check. It did not separate client kinds from server kinds.
- `docs/reference/ports-and-endpoints.md:501` lists the inbound kinds. `docs/how-to/orchestrate-app-shell-views-and-session-transitions.md:91-96` documents the client broadcast of `session_started`. Both are wrong after this task.
- DoR 9: no transitional acceptance of the old client frame.

## Product & User Story References
- PRD-0023 (App Shell and campaign hub).
- US-0065 Scenario 2 (DM launches the session) and Scenario 3 (a player does not see the launch control).
- US-0017 (DM narrative whispers stay private to the DM).

## Detailed Specification & Implementation Plan
1. Split the frame kinds in `session_frames.py` into one table that maps each client kind to its required `game_session` permission. Client kinds: `player_readiness`, `player_stand_in`, `token_action`, `aoe_placed`, `spell_vfx`, `confirm_ghost` (each `participate`). Remove `session_started` from the inbound table. The gateway start route is its only source.
2. For `turn_advanced`, `dice_rolled`, `token_moved` and `dm_whisper`: find the real producer of each. If no producer exists, remove the kind from the inbound table. If a DM client must send one (for example `dm_whisper`), require `session.control` for it. Record the decision per kind in the task commit and in `docs/reference/ports-and-endpoints.md`.
3. Change `may_publish_frame` to take the required permission from the table. Keep the `PERMISSION_DENIED` and `AUTHZ_UNAVAILABLE` error frames. The overlay socket (`overlay/frame_dispatch.py:65`) passes its own permission.
4. In `sessions_proxy.py`, decode the owner reply into a typed model with a required `status` field. A reply without `status` is an upstream contract error (502 through the existing upstream error mapping), not a `KeyError`.
5. In `frontend/src/app/session-actions.ts`, `launchSession` calls `POST /api/v1/sessions/{id}/start` through the shell request transport. On success it navigates. On failure it shows the owner message and stays in the lobby. It sends no socket frame.
6. In `frontend/src/app/session-socket.ts`, navigate on `session_started` only when `msg.sessionId` equals the shell session id and `msg.status === 'active'`. Navigate to the shell's own campaign and session ids, not to ids from the frame.
7. Update `docs/reference/ports-and-endpoints.md` and `docs/how-to/orchestrate-app-shell-views-and-session-transitions.md`. Add a `CHANGELOG.md` entry under `[Unreleased]` (Security).

## Frontdoor Blackbox Test Plan
- Python (gateway frontdoor, `tests/test_blackbox_campaign_and_lobby/test_session_lobby.py`): a DM and a player open session sockets. The player sends `{"type": "session_started", ...}`. Assert that the player gets an `UNKNOWN_FRAME` error frame and that the DM socket receives nothing. Then the DM calls `POST /api/v1/sessions/{id}/start`. Assert that both sockets receive `session_started` with `status: "active"`.
- Python: for each kind kept with `control`, a player frame gets `PERMISSION_DENIED` and the DM frame is relayed.
- Python: an owner start reply without `status` (live loopback upstream, see `docs/how-to/test-cross-service-calls-with-live-upstreams.md`) gives a 5xx with a fixed detail, not a `KeyError` trace.
- Frontend unit (`frontend/test/app_shell/session-transitions.test.ts`): launch calls the start route; a failed start keeps the lobby; a `session_started` frame for another session id does not navigate.
- Playwright BDD (`e2e/features/session_lobby_and_vtt.feature`, "DM Launching Active Tabletop VTT"): after launch, `GET /api/v1/sessions/{id}` returns `status: "active"`.

## Definition of Done
- No client can cause a `session_started` frame. Every inbound kind has an explicit permission.
- The App Shell launch moves the session to `active` through the owner.
- Docs and `CHANGELOG.md` updated. `uv run pytest`, `pnpm run build`, `make build`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: high
- Source audits: `gateways-libs.md` (F3), verified and widened by the refactor-r3 synthesis
