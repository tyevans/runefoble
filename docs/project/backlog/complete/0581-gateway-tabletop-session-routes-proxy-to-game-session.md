---
id: '0581'
title: Gateway Tabletop Session Routes Proxy to Game Session
status: Complete
created: 2026-11-17
dependencies:
- TASK-0580
governing_adrs:
- ADR-0002
- ADR-0007
- ADR-0011
governing_prds:
- PRD-0001
- PRD-0023
governing_stories:
- US-0065
- US-0014
target_release: 0.9.0
---

# TASK-0581: Gateway Tabletop Session Routes Proxy to Game Session

## Status
Complete

## Summary
Replace the canned session handlers in `gateway/api/src/gateway_api/routers/tabletop.py` with proxies to `game_session`. The gateway keeps its public paths. It forwards each call through the shared client from TASK-0580. Two routes have no owner route yet (`dm-override`, `atmosphere`). Add them to `game_session` in this task. The canned code and the magic IDs are deleted.

## Problem Statement
- `tabletop.py:31-48` returns a fabricated session. It uses hardcoded campaign `"4"` and session IDs `"14"` and `"15"`, and a fixed `current_turn: "c1"`.
- `tabletop.py:51-62` writes only to the in-memory `campaign_store`.
- `tabletop.py:122-131` (advance turn) echoes the request. It does not advance a turn.
- `tabletop.py:134-156` (`dm-override`, `atmosphere`) reports success and changes nothing.
- No handler calls `game_session` (`w1-gateway-api.md` F7, F12; `w3-ddd-architecture.md` F3).
- The owner has real routes. `game_session` exposes `GET /api/v1/sessions/{session_id}`, `POST /api/v1/sessions/{session_id}/start`, `POST .../next-turn`, `POST .../hot-swap` (`services/game_session/src/game_session/routers/session.py`, and the hot-swap router).

## Documentation & Architecture Review
- ADR-0007 places session state in the owning BC. The gateway holds no session state.
- ADR-0011: aggregate state changes go through `DeclarativeAggregate` and `AggregateRepository`. New `game_session` commands follow that rule.
- `docs/how-to/manage-campaign-lifecycle-and-invites.md` and `docs/reference/ports-and-endpoints.md:233-270` list the session routes as gateway routes. Keep the public paths. Update the docs for any path that changes.
- Authorization of these routes (`play`, `run_session`) is owned by the authorization theme. This task forwards the caller identity and keeps the existing gateway check. It does not change the SpiceDB model.

## Product & User Story References
- [`prd-0001-the-watcher-ai-dm-and-board-animator.md`](../../product/accepted/prd-0001-the-watcher-ai-dm-and-board-animator.md)
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`us-0065-game-session-lobby-readiness-and-launch.md`](../../user_stories/accepted/us-0065-game-session-lobby-readiness-and-launch.md)
- [`us-0014-realtime-board-websocket-sync.md`](../../user_stories/accepted/us-0014-realtime-board-websocket-sync.md)

## Detailed Specification & Implementation Plan
1. Map each public route to an owner route:

| Gateway route | Owner route | Status |
|---|---|---|
| `GET /api/v1/sessions/{session_id}` | `GET /api/v1/sessions/{session_id}` | exists |
| `POST /api/v1/sessions/{session_id}/start` | `POST /api/v1/sessions/{session_id}/start` | exists |
| `POST /api/v1/sessions/{session_id}/hot-swap` | `POST /api/v1/sessions/{session_id}/hot-swap` | exists |
| `POST /api/v1/sessions/{session_id}/turns/advance` | `POST /api/v1/sessions/{session_id}/next-turn` | exists |
| `POST /api/v1/sessions/{session_id}/dm-override` | none | add to `game_session` |
| `POST /api/v1/sessions/{session_id}/atmosphere` | none | add to `game_session` |

2. In `services/game_session`, add the two missing routes. Each route calls one aggregate command. Each command emits a domain event through `BaseRunefobleEvent` and `@register_event`. Add the atmosphere fields to the session aggregate. Keep each new file under 300 lines.
3. Replace each handler in `tabletop.py` with a call through the shared client. Delete the `campaign_store` writes, the magic IDs and the canned payloads. Keep only the session routes in this file. The token and board routes move to TASK-0582. The speak-and-act route moves to TASK-0583.
4. Move the session routes to `gateway/api/src/gateway_api/routers/sessions_proxy.py` so that `tabletop.py` can be removed by TASK-0582 and TASK-0583.
5. Update `docs/reference/ports-and-endpoints.md` for the two new owner routes.

## Frontdoor Blackbox Test Plan
Test file: `tests/test_blackbox_gateway_session_proxy.py`. The gateway and `game_session` run as ASGI apps. Setup goes through public routes: create the session with `POST /api/v1/sessions/create`, then call the gateway.

| Case | Expected before fix | Expected after fix |
|---|---|---|
| `GET /api/v1/sessions/{id}` returns the created session id | Fails: canned id `"14"` or `"15"` | Passes |
| `POST .../turns/advance` changes `current_turn` seen on the next GET | Fails: echo only | Passes |
| `POST .../dm-override` returns the owner event id and the next GET shows the override | Fails: no state change | Passes |
| `POST .../atmosphere` then GET shows the new lighting | Fails: no state change | Passes |
| Owner down returns 503 | Fails: canned 200 | Passes |

No test may assert a fixed string such as `"Valeros"` or `"Session 14"`.

## Definition of Done
1. `tabletop.py` no longer contains a canned payload. `rg "Valeros|campaign_store" gateway/api/src/gateway_api/routers/` returns no match in session routes.
2. Both new `game_session` routes exist, are in the OpenAPI schema, and have event tests.
3. The gateway forwards through `ServiceClient` (TASK-0580). It does not call `game_session` internals.
4. The blackbox test file above passes. `uv run ruff check .` passes.
5. `docs/reference/ports-and-endpoints.md` matches the routes.

## Orchestrator Addenda (2026-11-17, round 2)

Source: `.audit/synth/discovered-round2.md`.

- The hot-swap route in gateway/api/src/gateway_api/routers/tabletop.py (about line 101) clears the gateway store flag and never calls character_sheet. Proxy hot-swap to game_session and character_sheet, and remove the store write.

## Audit Provenance

- Severity: critical
- Source audits: `w1-gateway-api.md`, `w3-ddd-architecture.md`, `w1-game-session.md`
