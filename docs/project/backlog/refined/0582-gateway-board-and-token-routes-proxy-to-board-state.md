---
id: '0582'
title: Gateway Board and Token Routes Proxy to Board State
status: Refined
created: 2026-11-17
dependencies:
- TASK-0580
- TASK-0581
governing_adrs:
- ADR-0002
- ADR-0006
- ADR-0007
governing_prds:
- PRD-0005
- PRD-0003
governing_stories:
- US-0014
- US-0043
target_release: 0.9.0
---

# TASK-0582: Gateway Board and Token Routes Proxy to Board State

## Status
Refined

## Summary
Route the board and token reads and writes from the gateway to `board_state`. The gateway forwards with the shared client from TASK-0580. Two gateway routes have no session id, so they cannot reach an owner aggregate. Remove them. Callers use the session-scoped `board_state` routes instead. The canned board and token handlers are deleted.

## Problem Statement
- `tabletop.py:159-172` (token move and get) returns fixed coordinates `x=2, y=3`. A move changes nothing (`w1-board-state.md` F4).
- `tabletop.py:175-180` (`GET /api/v1/boards/{session_id}`) returns the fixed `DEFAULT_BOARD_TOKENS`.
- No gateway route reaches `board-state:8002`. The ingress sends only `/api` to the gateway. The board WebSocket route in `board_state` is `/ws/boards/{session_id}`, so the gateway must not depend on it here (`w1-board-state.md` F4).
- `frontend/src/services/app-data-service.ts` falls back to fixtures on failure. Client changes are out of this task's scope.

## Documentation & Architecture Review
- `board_state` owns the grid, the tokens and the movement rules (`docs/reference/architecture-overview.md`).
- The owner routes exist in `services/board_state/src/board_state/`: `GET /api/v1/boards/{session_id}`, `GET /api/v1/boards/{session_id}/visibility`, `POST /api/v1/boards/{session_id}/tokens/{token_id}/move`, `POST /api/v1/boards/{session_id}/tokens`.
- There is no owner route for `GET` of one token. Add it as `GET /api/v1/boards/{session_id}/tokens/{token_id}` in `board_state`. It reads the same aggregate as the board read.
- `board_state` reads the SpiceDB key from a missing setting and falls back to a literal (`w3-ddd-architecture.md` F9). TASK-0625 fixes that. This task does not change the SpiceDB factory.

## Product & User Story References
- [`prd-0005-realtime-websocket-board-sync.md`](../../product/accepted/prd-0005-realtime-websocket-board-sync.md)
- [`prd-0003-spatial-fog-of-war-and-visibility-engine.md`](../../product/accepted/prd-0003-spatial-fog-of-war-and-visibility-engine.md)
- [`us-0014-realtime-board-websocket-sync.md`](../../user_stories/accepted/us-0014-realtime-board-websocket-sync.md)
- [`us-0043-tactile-kinetic-board-and-spoken-ghost-previews.md`](../../user_stories/accepted/us-0043-tactile-kinetic-board-and-spoken-ghost-previews.md)

## Detailed Specification & Implementation Plan
1. Gateway routes and their owner targets:

| Gateway route (public) | Owner route | Action |
|---|---|---|
| `GET /api/v1/boards/{session_id}` | `GET /api/v1/boards/{session_id}` | proxy |
| `POST /api/v1/boards/{session_id}/tokens/{token_id}/move` | `POST /api/v1/boards/{session_id}/tokens/{token_id}/move` | proxy (new public route) |
| `GET /api/v1/boards/{session_id}/tokens/{token_id}` | added to `board_state` | proxy (new) |
| `POST /api/v1/board/tokens/{token_id}/move` | none (no session id) | delete |
| `GET /api/v1/board/tokens/{token_id}` | none (no session id) | delete |

2. Add `GET /api/v1/boards/{session_id}/tokens/{token_id}` to `services/board_state`. Return 404 when the token does not exist.
3. Create `gateway/api/src/gateway_api/routers/boards_proxy.py`. Forward each route through the shared client. Delete the two handlers and `DEFAULT_BOARD_TOKENS` from `tabletop.py`.
4. Delete the board and token handlers from `tabletop.py`. Keep `tabletop.py` only if `speak-and-act` still needs it. TASK-0583 removes it.
5. Update `docs/reference/ports-and-endpoints.md` and `docs/reference/events-schema.md` for the removed routes. Tell the client team in the PR that the sessionless token routes are gone.

## Frontdoor Blackbox Test Plan
Test file: `tests/test_blackbox_gateway_board_proxy.py`. `board_state` runs as an ASGI app behind the gateway. Setup: create a board with `POST /api/v1/boards`, add a token with `POST /api/v1/boards/{session_id}/tokens`.

| Case | Expected before fix | Expected after fix |
|---|---|---|
| Move a token through the gateway, then GET the board | Fails: board never changes | Passes: token position changed |
| GET one token returns the stored `x`, `y` | Fails: fixed `x=2, y=3` | Passes |
| Unknown token returns 404 | Fails: 200 with fixed token | Passes |
| Sessionless `POST /api/v1/board/tokens/{id}/move` returns 404 | Fails: 200 | Passes |
| Board service down returns 503 | Fails: canned 200 | Passes |

## Definition of Done
1. No canned board or token payload remains in `gateway/api/src`. `rg "DEFAULT_BOARD_TOKENS|token_moved" gateway/api/src` returns nothing.
2. The new `board_state` token GET route is in its OpenAPI schema.
3. The gateway forwards through `ServiceClient`.
4. The blackbox test file passes. `uv run ruff check .` passes.
5. `docs/reference/ports-and-endpoints.md` shows the public board routes.

## Audit Provenance

- Severity: critical
- Source audits: `w1-board-state.md`, `w1-gateway-api.md`, `w3-ddd-architecture.md`
