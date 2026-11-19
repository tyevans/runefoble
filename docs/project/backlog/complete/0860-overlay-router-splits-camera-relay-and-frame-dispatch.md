---
id: '0860'
title: Overlay Router Splits Camera Relay, Frame Dispatch, and Routes
status: Complete
created: 2026-11-18
dependencies:
- TASK-0743
governing_adrs:
- ADR-0015
- ADR-0013
governing_prds: []
governing_stories: []
target_bc: gateway
target_release: 0.9.0
---
# TASK-0860: Overlay Router Splits Camera Relay, Frame Dispatch, and Routes

## Status
Complete

## Summary
`gateway/api/src/gateway_api/routers/overlay.py` (290 lines) holds HTTP routes, two camera relays, error mapping, and a frame dispatcher. The two camera relays repeat the same owner call, error mapping, and broadcast. The dispatcher is an `if`/`elif` chain on action sets. The spectator route imports the overlay endpoint inside its function body. The fix splits the module by responsibility and registers the spectator route from the same endpoint object.

## Problem Statement
- `overlay.py:154-187` (`_relay_turn_started`) and `:189-225` (`_relay_token_moved`): the same owner call, the same three-type `except`, `_send_camera_error`, and a `camera_target_updated` broadcast.
- `overlay.py:227-261` (`_handle_overlay_frame`): `if`/`elif` on `TURN_STARTED_ACTIONS`, `TOKEN_MOVED_ACTIONS`, and `ROLL_ACTIONS`. Each new action edits this function.
- `gateway/api/src/gateway_api/routers/spectator.py:44-48`: `/ws/spectator/{session_id}` imports `overlay_websocket_endpoint` inside the handler and calls it. It is a copy of the route, not a registration.

## Documentation & Architecture Review
- ADR-0015 (b): the gateway relays and aggregates. The camera relay keeps no domain state.
- ADR-0013: the overlay is a view. Keep the frame types for the overlay client unchanged.
- TASK-0743 (refined) moves gateway WebSocket routes into one router. Land it first.
- TASK-0316 (proposed) is stale. Its file is 56 lines. See the index correction.
- `docs/how-to/broadcast-obs-stream-overlay-and-cinematic-camera.md`: update the module references.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Create `gateway_api/overlay/camera_relay.py` for owner calls, error mapping, and one broadcast helper used by both camera actions.
2. Create `gateway_api/overlay/frame_dispatch.py` with a table from action set to handler. Adding an action adds a table row.
3. Keep `routers/overlay.py` for HTTP and WebSocket routes only.
4. Register `/ws/spectator/{session_id}` with the same endpoint object at module level. Remove the in-function import.
5. Keep close codes and frame types unchanged.

## Frontdoor Blackbox Test Plan
- Existing tests in `tests/test_overlay_modular_decomposition.py` (JSON route, camera relay, `INVALID_FRAME`, unknown token) pass unchanged.
- Connect to `/ws/spectator/{id}` and `/ws/overlay/{id}`. Assert the same frames for the same input.

## Definition of Done
- `routers/overlay.py` holds routes only. No module in the new package is over 300 lines.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: low
- Source audits: `refactor-r2/gateways.md` (F2, F10)
