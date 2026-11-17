---
id: '0596'
title: Gateway The Watcher Public Routes Proxy to The Watcher Service
status: Refined
created: 2026-11-17
dependencies:
- TASK-0580
- TASK-0583
governing_adrs:
- ADR-0002
- ADR-0007
governing_prds:
- PRD-0001
- PRD-0002
- PRD-0017
governing_stories:
- US-0002
- US-0003
- US-0057
severity: high
source_audits:
- w3-ddd-architecture.md
- w1-the-watcher.md
- w1-gates-infra.md
target_release: 0.9.0
---

# TASK-0596: Gateway The Watcher Public Routes Proxy to The Watcher Service

## Status
Refined

## Summary
The gateway has no route to `the_watcher`, except the canned speak-and-act route (TASK-0583). The ports reference names more than 30 public Watcher routes: faction agendas, world ticks, stand-ins, whispers, proposals and approvals, intent, narration and scenes. Add a gateway proxy for each public route. The gateway does not run Watcher logic and does not hold any Watcher state.

## Problem Statement
- `docs/reference/ports-and-endpoints.md:66-70` and the other Watcher rows name public routes such as `POST /api/v1/campaigns/{campaign_id}/world-tick`. Browsers reach only `/api` on the gateway, so none of these routes is reachable (`w3-ddd-architecture.md` Deliverable 1, `w1-gates-infra.md` F2).
- The Watcher's LLM path and the inference worker URLs are wired by TASK-0624 (Helm). This task does not change them.
- `the_watcher` owns stand-in and veto logic. The gateway must not add a check that replaces the owner's check (ADR-0002 section 3, PRD-0002).

## Documentation & Architecture Review
- ADR-0002: The Watcher is an assistant. Players and human DMs keep veto and override authority. The proxy must forward `veto` and `approve` calls unchanged, so the owner applies the DM decision.
- Route list source: `docs/reference/ports-and-endpoints.md` (the-watcher rows) and `services/the_watcher/src/the_watcher/routers/`. The owner lists about 35 routes. Route `POST /api/v1/watcher/speak-and-act` belongs to TASK-0583 and is excluded here.
- Internal routes (for example the `/the-watcher/...` alias paths in the owner) are not proxied. Do not proxy an owner alias (DoR 9).

## Product & User Story References
- [`prd-0001-the-watcher-ai-dm-and-board-animator.md`](../../product/accepted/prd-0001-the-watcher-ai-dm-and-board-animator.md)
- [`prd-0002-missing-player-ai-stand-in-with-penalties.md`](../../product/accepted/prd-0002-missing-player-ai-stand-in-with-penalties.md)
- [`prd-0017-autonomous-npc-faction-agendas-and-world-simulation.md`](../../product/accepted/prd-0017-autonomous-npc-faction-agendas-and-world-simulation.md)
- [`us-0002-absent-player-mimicked-by-ai-with-penalties.md`](../../user_stories/accepted/us-0002-absent-player-mimicked-by-ai-with-penalties.md)
- [`us-0003-dm-adjudicates-scene-with-ai-assistance.md`](../../user_stories/accepted/us-0003-dm-adjudicates-scene-with-ai-assistance.md)
- [`us-0057-autonomous-npc-faction-agendas-and-world-simulation.md`](../../user_stories/accepted/us-0057-autonomous-npc-faction-agendas-and-world-simulation.md)

## Detailed Specification & Implementation Plan
1. Build the route list from `docs/reference/ports-and-endpoints.md` (rows with `the-watcher` and a public `/api/v1` path). Put the list in a table in `docs/reference/gateway-route-ownership.md` (created by TASK-0598). Mark each row "proxy" or "internal".
2. Create `gateway/api/src/gateway_api/routers/watcher_proxy.py` (one router). If the file exceeds 300 lines, split into `watcher_proxy_factions.py`, `watcher_proxy_intent.py` and `watcher_proxy_dm.py`.
3. Each handler forwards through `ServiceClient` (TASK-0580). It passes the path, query and JSON body unchanged, and the caller identity. Do not read the body's `user_id`, `approver_id` or `dm_id`.
4. Set the timeout for `narrate`, `scenes/generate` and `whispers/generate` from the owner's LLM budget. Take the value from the settings field, not from a literal in the router.
5. Add `THE_WATCHER` (TASK-0580) to the settings. Confirm the Helm variable from TASK-0624.
6. Record each route's owner status in `docs/reference/gateway-route-ownership.md`.

## Frontdoor Blackbox Test Plan
Test file: `tests/test_blackbox_gateway_watcher_proxy.py`. `the_watcher` runs as an ASGI app.

| Case | Expected before fix | Expected after fix |
|---|---|---|
| `GET /api/v1/campaigns/{id}/factions` after a `POST` through the gateway returns the faction | Fails: 404 | Passes |
| World tick through the gateway returns the owner's bulletin | Fails: 404 | Passes |
| DM veto through the gateway removes a proposal (owner state) | Fails: 404 | Passes |
| Stand-in act through the gateway returns the owner's guardrail result | Fails: 404 | Passes |
| Owner down returns 503 | Fails: 404 | Passes |

## Definition of Done
1. Every route marked "proxy" in `gateway-route-ownership.md` answers through the gateway.
2. No Watcher logic or Watcher state lives in `gateway/api`.
3. The blackbox test file passes. `uv run ruff check .` passes.
4. `docs/reference/ports-and-endpoints.md` shows the gateway as the browser endpoint for the proxied routes.
