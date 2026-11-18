---
id: '0584'
title: Gateway Downtime Routes Proxy to Game Session and Character Sheet
status: Complete
created: 2026-11-17
dependencies:
- TASK-0580
governing_adrs:
- ADR-0001
- ADR-0007
- ADR-0011
governing_prds:
- PRD-0014
- PRD-0024
governing_stories:
- US-0044
- US-0047
target_release: 0.9.0
---

# TASK-0584: Gateway Downtime Routes Proxy to Game Session and Character Sheet

## Status
Complete

## Summary
Replace the canned downtime handlers in `gateway/api/src/gateway_api/routers/downtime.py` (removed) with proxies. Stronghold, campfire, tavern and haggling calls go to `game_session`. Recipe combine goes to `character_sheet`. The fixed gold balance, the fixed campsite and the formula payloads are deleted.

## Problem Statement
- `downtime.py:19-35` returns a fixed `treasury_gold: 100` and a "Party Campsite" for every campaign.
- `downtime.py:62-89` (stronghold upgrade) returns `status: "upgraded"`. It deducts no gold and stores nothing (`w1-gateway-api.md` F8).
- `downtime.py:66-160` (campfire, crafting, tavern, haggling) returns fixed or formula payloads. None calls a service (`w3-ddd-architecture.md` F3).
- The owners already implement these flows. Examples: `game_session` `GET /api/v1/campaigns/{campaign_id}/stronghold`, `POST /api/v1/sessions/{session_id}/rest/campfire`, `POST /api/v1/sessions/{session_id}/tavern/games`. `character_sheet` has `POST /recipes/combine` in `crafting_router.py`.

## Documentation & Architecture Review
- `docs/reference/downtime-and-crafting-events.md:87-90` and `docs/reference/tavern-and-merchants-events.md:103-106` list these routes as "`game_session` / `gateway`". After this task the gateway is only a proxy. Update both tables.
- ADR-0011: stronghold and campfire state change through aggregates. The gateway must not write gold.
- The `game_session` owner route for haggling is `POST /api/v1/haggling/start` with `POST /api/v1/haggling/{negotiation_id}/accept` and `.../gambit`. The gateway route `POST /api/v1/sessions/{session_id}/merchants/{merchant_id}/haggle` has no direct owner route. Map it in the plan below or record it as a gap.

## Product & User Story References
- [`prd-0014-downtime-crafting-and-stronghold-engine.md`](../../product/accepted/prd-0014-downtime-crafting-and-stronghold-engine.md)
- [`prd-0024-settlement-haven-builder-and-mobile-minigames.md`](../../product/accepted/prd-0024-settlement-haven-builder-and-mobile-minigames.md)
- [`us-0044-interactive-campfire-downtime-and-crafting.md`](../../user_stories/accepted/us-0044-interactive-campfire-downtime-and-crafting.md)
- [`us-0047-tavern-minigames-and-merchant-haggling.md`](../../user_stories/accepted/us-0047-tavern-minigames-and-merchant-haggling.md)

## Detailed Specification & Implementation Plan
1. Map each route. Verify each owner path and method in its router before coding. Record any difference in the PR.

| Gateway route | Owner | Owner route |
|---|---|---|
| `GET /api/v1/campaigns/{id}/stronghold` | game_session | `GET /api/v1/campaigns/{campaign_id}/stronghold` |
| `POST /api/v1/campaigns/{id}/stronghold/upgrade` | game_session | `POST /api/v1/campaigns/{campaign_id}/stronghold` (verify the body shape) |
| `POST /api/v1/sessions/{id}/rest/campfire` | game_session | `POST /api/v1/sessions/{session_id}/rest/campfire` |
| `POST /api/v1/crafting/recipes/combine` | character_sheet | `POST /recipes/combine` (verify the router prefix) |
| `POST /api/v1/sessions/{id}/tavern/games` | game_session | `POST /api/v1/sessions/{session_id}/tavern/games` |
| `POST /api/v1/sessions/{id}/merchants/{mid}/haggle` | game_session | map to `POST /api/v1/haggling/start`, or add the route to `game_session` |

2. Create `gateway/api/src/gateway_api/routers/downtime_proxy.py`. Forward each route through `ServiceClient` (TASK-0580). Pass the caller identity. Do not read the body's `user_id`.
3. Delete `downtime.py` and its fixed payloads, the gold literal and the formula code. Keep the router mounted from the same place in `main.py`.
4. If an owner route is missing, add it to the owner in the same change. Keep each owner change in its own router file.
5. Update `docs/reference/downtime-and-crafting-events.md` and `docs/reference/tavern-and-merchants-events.md` so the table names the owner.

## Frontdoor Blackbox Test Plan
Test file: `tests/test_blackbox_gateway_downtime_proxy.py`. `game_session` and `character_sheet` run as ASGI apps. Setup: create the campaign stronghold and the session through public routes.

| Case | Expected before fix | Expected after fix |
|---|---|---|
| Stronghold GET returns the stored treasury | Fails: fixed `100` | Passes |
| Upgrade reduces treasury on the next GET | Fails: unchanged | Passes |
| Campfire rest returns the owner boon list | Fails: fixed boons | Passes |
| Recipe combine returns the owner outcome | Fails: formula payload | Passes |
| Insufficient gold returns the owner 409 or 422 | Fails: 200 | Passes |

## Definition of Done
1. `downtime.py` is removed. `rg "Party Campsite|treasury_gold: 100" gateway/api/src` returns nothing.
2. Every row in the table forwards through `ServiceClient`.
3. The blackbox test file passes. `uv run ruff check .` passes.
4. The two event reference docs name the real owner.

## Audit Provenance

- Severity: high
- Source audits: `w1-gateway-api.md`, `w3-ddd-architecture.md`
