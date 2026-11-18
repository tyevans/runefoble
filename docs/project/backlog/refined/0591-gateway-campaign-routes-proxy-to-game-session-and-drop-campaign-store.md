---
id: '0591'
title: Gateway Campaign Routes Proxy to Game Session and Drop Campaign Store
status: Refined
created: 2026-11-17
dependencies:
- TASK-0580
- TASK-0590
governing_adrs:
- ADR-0001
- ADR-0007
governing_prds:
- PRD-0023
governing_stories:
- US-0063
- US-0071
- US-0009
severity: critical
source_audits:
- w1-gateway-api.md
- w1-game-session.md
- w3-ddd-architecture.md
target_release: 0.9.0
---

# TASK-0591: Gateway Campaign Routes Proxy to Game Session and Drop Campaign Store

## Status
Refined

## Summary
After TASK-0590, `game_session` owns campaigns. This task replaces `gateway/api/src/gateway_api/routers/campaigns.py` and the `campaign_store` package with proxies. The gateway keeps only its own WebSocket fan-out for campaigns. The gateway no longer writes SpiceDB tuples for campaigns.

## Problem Statement
- `routers/campaigns.py` (209 lines) serves 11 routes from `campaign_store` (`w1-gateway-api.md` F11).
- `campaign_store/` (about 330 lines across `store.py`, `sessions.py`, `invites.py`, `queries.py`) holds state that a restart loses (`w3-ddd-architecture.md` F6).
- The router writes SpiceDB relations inline (`campaigns.py:43-55`, `:88-103`, `:185`). That breaks the rule that the owner writes state (`w1-gateway-api.md` F11).
- `campaign_store/queries.py` has `known_names = {"user-valeros": "Valeros", ...}` (`w1-gateway-api.md` F12).

## Documentation & Architecture Review
- ADR-0007: the gateway does routing, auth and aggregation only. Campaign state moves to the owner (TASK-0590).
- `docs/how-to/manage-campaign-lifecycle-and-invites.md` describes the public contract. The paths do not change.
- The campaign WebSocket (`/ws/campaigns/{id}`, `gateway/api/src/gateway_api/websocket.py`) stays in the gateway. It is fan-out, not domain state. It checks `view` before it accepts a socket. Do not change its auth in this task.
- `POST /api/v1/campaigns/{id}/roles` is in the same router. Its missing authorization belongs to the authorization theme. Do not ship this task before that fix (see TASK-0590, step 5).

## Product & User Story References
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`us-0071-campaign-dashboard-idempotency-and-lifecycle.md`](../../user_stories/accepted/us-0071-campaign-dashboard-idempotency-and-lifecycle.md)

## Detailed Specification & Implementation Plan
1. Create `gateway/api/src/gateway_api/routers/campaigns_proxy.py`. Forward every route in the table to `game_session` through `ServiceClient` (TASK-0580). Pass the caller identity. Do not read the body's `user_id`.

| Gateway route | Owner route (TASK-0590) |
|---|---|
| `GET /api/v1/campaigns` | same |
| `POST /api/v1/campaigns` | same |
| `GET`, `PATCH /api/v1/campaigns/{campaign_id}` | same |
| `POST /api/v1/campaigns/{campaign_id}/invites` | same |
| `POST /api/v1/campaigns/join` | same |
| `GET /api/v1/campaigns/{campaign_id}/members` | same |
| `DELETE /api/v1/campaigns/{campaign_id}/members/{user_id}` | same |
| `GET`, `POST /api/v1/campaigns/{campaign_id}/sessions` | same |
| `POST /api/v1/campaigns/{campaign_id}/roles` | owner route from TASK-0590 step 5. Move this row only after the authorization fix for role assignment is merged. Do not keep a stub. |

2. Delete `routers/campaigns.py`, `campaign_store/` and the `known_names` mapping.
3. Remove every SpiceDB write from the gateway (`rg "write_relationship" gateway/api/src` must return only the auth-theme files).
4. Remove the `CAMPAIGN_STORE` singleton import from `main.py` and `dependencies.py`.
5. Update the `docs/how-to/manage-campaign-lifecycle-and-invites.md` text for the owner name and the response shape changes, if any.

## Frontdoor Blackbox Test Plan
Test file: `tests/test_blackbox_gateway_campaigns_proxy.py` (replaces `tests/test_blackbox_gateway_campaigns.py`, `test_blackbox_gateway_campaign_sessions.py` and `test_blackbox_gateway_campaign_store_decomposition.py` assertions that depend on the store). `game_session` runs as an ASGI app.

| Case | Expected before fix | Expected after fix |
|---|---|---|
| Create, join with invite, list members through the gateway | Passes only via store | Passes via owner |
| Gateway app rebuilt with the same owner: campaign still listed | Fails: store lost | Passes |
| Owner down returns 503 on list | Fails: store answer | Passes |
| `rg "campaign_store" gateway/api` | Fails: matches | Passes: no match |

## Definition of Done
1. `routers/campaigns.py` and `campaign_store/` are removed.
2. Every route in the table forwards through `ServiceClient`. The roles route follows TASK-0590 step 5.
3. The gateway writes no SpiceDB campaign tuple.
4. The blackbox test file passes. Obsolete store tests are removed in the same PR.
5. `uv run ruff check .` passes.

## Orchestrator Addenda (2026-11-17)

Source: `.audit/synth/discovered-round1.md`.

- `GET /api/v1/campaigns/{campaign_id}` returns HTTP 200 with a fabricated campaign for an unknown id (`gateway/api/src/gateway_api/routers/campaigns.py:61-72`). Return 404. This also unblocks the `@blocked` scenario in `e2e/features/app_shell_data_errors.feature`.

## Orchestrator Addenda (2026-11-17, round 2)

Source: `.audit/synth/discovered-round2.md`.

- frontend/src/fixtures/app-data-service.fixtures.ts uses camp- ids. Replace them with the ids that the proxied game_session routes return.
