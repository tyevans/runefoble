---
id: '0592'
title: Gateway Settlement REST and Minigame WebSocket Proxy to Game Session
status: Complete
created: 2026-11-17
dependencies:
- TASK-0580
governing_adrs:
- ADR-0006
- ADR-0007
governing_prds:
- PRD-0024
- PRD-0023
governing_stories:
- US-0074
- US-0076
target_release: 0.9.0
---

# TASK-0592: Gateway Settlement REST and Minigame WebSocket Proxy to Game Session

## Status
Complete

## Summary
`gateway/api/src/gateway_api/main.py` imports `game_session.settlement.router` and `game_session.routers.minigames_ws` and mounts them in the gateway process. The gateway therefore loads game-session code, and its state lives in the gateway process. Replace both mounts with HTTP proxies for REST and a byte relay for WebSockets.

## Problem Statement
- `main.py:10` imports `game_session.settlement.router`. It mounts `settlement_haven_router` at `main.py:79` (`w3-ddd-architecture.md` F12, `w1-gateway-api.md` F10).
- `main.py:140` and `:151` import `game_session.routers.minigames_ws.handle_table_websocket` lazily, for the minigame sockets (`w3-ddd-architecture.md` Deliverable 2).
- The owner routes are `GET`/`POST /api/v1/campaigns/{id}/settlements`, `/api/v1/settlements/...`, `/api/v1/establishments/...`, and the sockets `/ws/establishments/{establishment_id}/tables/{table_id}` and `/ws/minigames/{table_id}` (`services/game_session/src/game_session/`).
- The gateway's domain state for settlements and minigames is whatever the in-process code keeps in memory (`w1-game-session.md` F4).

## Documentation & Architecture Review
- ADR-0006: game events go through Redis Streams. The gateway relays sockets only.
- `docs/reference/tavern-and-merchants-events.md` lists the minigame routes. Keep the paths.
- A WebSocket relay is gateway fan-out, which ADR-0002 allows. The gateway must not parse minigame messages. It forwards frames in both directions.
- Authorization of the sockets is owned by the authorization theme. The relay forwards the verified identity on connect and does not add a check of its own.

## Product & User Story References
- [`prd-0024-settlement-haven-builder-and-mobile-minigames.md`](../../product/accepted/prd-0024-settlement-haven-builder-and-mobile-minigames.md)
- [`us-0074-interactive-mobile-tavern-and-casino-minigames.md`](../../user_stories/accepted/us-0074-interactive-mobile-tavern-and-casino-minigames.md)
- [`us-0076-town-bulletin-board-civic-rumors-and-bounties.md`](../../user_stories/accepted/us-0076-town-bulletin-board-civic-rumors-and-bounties.md)

## Detailed Specification & Implementation Plan
1. Create `gateway/api/src/gateway_api/routers/settlements_proxy.py`. Forward each settlement REST route through `ServiceClient` (TASK-0580). List the routes from `services/game_session/src/game_session/settlement/router.py` and map each one. Do not invent routes.
2. Create `gateway/api/src/gateway_api/websocket_relay.py` (one module, under 200 lines). It opens an upstream WebSocket to `game_session` with the same path. It relays text and binary frames both ways. It closes both sides when either side closes. It uses the `websockets` client library, which must be added to `gateway/api/pyproject.toml` with `uv add`.
3. Replace the lazy imports at `main.py:140` and `:151` with calls to `websocket_relay`. The routes keep their public paths.
4. Remove `from game_session...` from `gateway/api/src`. Keep `game_session` in the gateway's `pyproject.toml` only if another import remains. Record that in the PR.
5. Update `docs/reference/ports-and-endpoints.md` and `docs/reference/tavern-and-merchants-events.md` where the gateway is named as the owner.

## Frontdoor Blackbox Test Plan
Test file: `tests/test_blackbox_gateway_settlement_proxy.py`. `game_session` runs as an ASGI app for REST and as a real uvicorn server for the WebSocket relay test.

| Case | Expected before fix | Expected after fix |
|---|---|---|
| `POST /api/v1/campaigns/{id}/settlements` through the gateway, then GET from the owner returns it | Fails: state in gateway process | Passes |
| Minigame socket echo: a frame sent through the gateway reaches the owner and comes back | Fails: in-process handler | Passes |
| Owner socket closed: the gateway closes the client socket | Fails: no relay | Passes |
| `rg "from game_session" gateway/api/src` | Fails: matches | Passes: no match |

## Definition of Done
1. `main.py` has no import from `game_session`.
2. Settlement REST and both minigame sockets go to the owner.
3. The relay module is under 200 lines.
4. The blackbox test file passes. `uv run ruff check .` passes.

## Audit Provenance

- Severity: high
- Source audits: `w1-gateway-api.md`, `w1-game-session.md`, `w3-ddd-architecture.md`
