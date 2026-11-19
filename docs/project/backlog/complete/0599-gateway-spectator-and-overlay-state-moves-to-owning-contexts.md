---
id: '0599'
title: Gateway Spectator and Overlay State Moves to Owning Contexts
status: Complete
created: 2026-11-17
dependencies:
- TASK-0581
- TASK-0582
governing_adrs:
- ADR-0002
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0011
- PRD-0005
governing_stories:
- US-0006
- US-0029
- US-0030
target_release: 0.9.0
---

# TASK-0599: Gateway Spectator and Overlay State Moves to Owning Contexts

## Status
Complete

## Summary
The gateway generates spectator state and stores camera directors in process memory. `spectator.py` returns a generated default state for any session ID. `cinematic_director.py` keeps `_SESSION_DIRECTORS` in a module dict. Move spectator projection to `game_session` and camera logic to `board_state`. The gateway keeps only the routes that proxy to those owners. Overlay HTML may stay in the gateway as static presentation with no state.

## Problem Statement
- `gateway/api/src/gateway_api/spectator.py:82-115` and `:176-180` return a generated default state, with DM notes and conditions, for any session ID (`w3-ddd-architecture.md` F13).
- `cinematic_director.py:216-223` keeps `_SESSION_DIRECTORS` in process memory. A restart resets every camera (`w3-ddd-architecture.md` F13).
- `routers/overlay.py:61` (`GET /overlay/party-vitals/{session_id}`) and `:85-86` (`/overlay/ws/{id}`, `/ws/overlay/{id}`) have no session check (`w1-gateway-api.md` F23). Authentication of these routes is owned by the authorization theme. This task moves the data source.
- DM notes can appear in the spectator payload. The owner must sanitize them (`docs/how-to/broadcast-obs-stream-overlay-and-cinematic-camera.md`).

## Documentation & Architecture Review
- `docs/reference/architecture-overview.md` lists "spectator view" under `game_session`. The spectator projection belongs there (ADR-0007).
- Camera and cinematic direction is board tracking. It belongs to `board_state`. `docs/how-to/broadcast-obs-stream-overlay-and-cinematic-camera.md` describes it.
- ADR-0013: the overlay is a microfrontend. Its Lit component stays in its owner's `ui/` folder. Check `services/<bc>/ui/` before moving any component.
- This task supersedes TASK-0316 (spectator router decomposition). After the move the file has no reason to be decomposed in the gateway.

## Product & User Story References
- [`prd-0011-live-spectator-studio-and-audience-interactivity.md`](../../product/accepted/prd-0011-live-spectator-studio-and-audience-interactivity.md)
- [`prd-0005-realtime-websocket-board-sync.md`](../../product/accepted/prd-0005-realtime-websocket-board-sync.md)
- [`us-0006-realtime-spectator-stream-and-chronicle.md`](../../user_stories/accepted/us-0006-realtime-spectator-stream-and-chronicle.md)
- [`us-0029-spectator-dynamic-cinematic-auto-camera.md`](../../user_stories/accepted/us-0029-spectator-dynamic-cinematic-auto-camera.md)
- [`us-0030-obs-transparent-party-vitals-and-multi-track-audio.md`](../../user_stories/accepted/us-0030-obs-transparent-party-vitals-and-multi-track-audio.md)

## Detailed Specification & Implementation Plan
1. In `services/game_session`, add `spectator/` with a projection read model and `GET /api/v1/sessions/{session_id}/spectator`. The projection reads the session aggregate and the turn state. It removes DM-only fields before it returns data. Keep each file under 300 lines.
2. In `services/board_state`, add `camera/` with the cinematic director state. Persist it through `AggregateRepository`. Add `GET` and `POST` routes under `/api/v1/boards/{session_id}/camera`. Remove the module-level dict.
3. Overlay party vitals: `GET /api/v1/sessions/{session_id}/overlay/party-vitals` in `game_session` returns the sanitized projection. The gateway proxies the overlay route to it.
4. Gateway: replace `spectator.py`, `cinematic_director.py`, the spectator router and the overlay data calls with proxies through `ServiceClient` (TASK-0580). Keep `overlay_templates.py` only if it renders static HTML with no data. Delete `overlay_models.py` if its models move to the owners.
5. Overlay WebSocket relay: use the relay from TASK-0592 for `/overlay/ws/{id}` and `/ws/overlay/{id}`.
6. Update `docs/reference/ports-and-endpoints.md` for the spectator, overlay and camera routes.

## Frontdoor Blackbox Test Plan
Test file: `tests/test_blackbox_spectator_overlay_owner.py`. `game_session` and `board_state` run as ASGI apps. Setup goes through public routes only.

| Case | Expected before fix | Expected after fix |
|---|---|---|
| Spectator GET for an unknown session returns 404 | Fails: generated default state | Passes |
| Spectator GET for a real session omits DM-only notes | Fails: DM notes shown | Passes |
| Camera set through the gateway survives a gateway rebuild | Fails: module dict | Passes |
| Party vitals for a session equal the owner projection | Fails: gateway default | Passes |
| `rg "_SESSION_DIRECTORS|generated default" gateway/api/src` | Fails: matches | Passes: no match |

## Definition of Done
1. Spectator, camera and vitals data come from owners through proxies.
2. The gateway holds no session or camera state.
3. The blackbox test file passes. `uv run ruff check .` passes.
4. `docs/reference/ports-and-endpoints.md` matches the routes.
5. TASK-0316 is closed as superseded in the index.

## Audit Provenance

- Severity: medium
- Source audits: `w3-ddd-architecture.md`, `w1-gateway-api.md`

## Orchestrator Addenda (2026-11-17, refactor-r1)

- TASK-0599 (gateway spectator and overlay state): append "Remove `set_raw_session_state` and `clear_raw_session_state` and the `_RAW_SESSION_STORE` dict (`gateway/api/src/gateway_api/spectator.py:69-71`). Three tests write to it directly: `tests/test_blackbox_cinematic_director/test_obs_overlay_routes.py:63`, `tests/test_spectator_stream_overlay.py:144`, `tests/test_overlay_modular_decomposition.py:126`. Seed session state through game_session public routes and read it back through the OBS overlay route." (tests F1)

## Completion Note
Open item moved out of scope: spec item 3 asked for a game_session party-vitals route. The gateway builds the vitals from owner reads; a dedicated owner route waits for a product need.
