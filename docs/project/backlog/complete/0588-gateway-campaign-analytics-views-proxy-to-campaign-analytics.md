---
id: '0588'
title: Gateway Campaign Analytics Views Proxy to Campaign Analytics
status: Complete
created: 2026-11-17
dependencies:
- TASK-0587
governing_adrs:
- ADR-0006
- ADR-0007
governing_prds:
- PRD-0012
governing_stories:
- US-0040
- US-0054
target_release: 0.9.0
---

# TASK-0588: Gateway Campaign Analytics Views Proxy to Campaign Analytics

## Status
Complete

## Summary
Heatmap, MVP and timeline views in `hub_views.py` return canned combat data on any upstream failure. The summary route has no proxy and returns literal numbers. Replace all four with proxies to `campaign_analytics`. Delete `hub_views.py` after this task, because TASK-0587 removed the lore routes.

## Problem Statement
- `hub_views.py:16-24` returns the fallback for any exception and for any non-200 status, including 403, 404 and 500 (`w2-campaign-analytics.md` F4).
- Fallbacks at `hub_views.py:118-246` contain invented encounters, names and damage totals ("Valeros", 88 damage, "Breach of the Astral Crypt").
- `hub_views.py:104-115` (campaign summary) returns `total_combat_turns: 42` and `mvp_candidate: "Valeros"`. There is no proxy.
- The fallback field names (`grid_cols`, `milestone_id`, `importance`) do not match the service models (`w2-campaign-analytics.md` F4, F9).
- `CAMPAIGN_ANALYTICS_URL` defaults to the cluster service name and is not set in Helm (`w1-gateway-api.md` F15).

## Documentation & Architecture Review
- Owner routes: `services/campaign_analytics/src/campaign_analytics/routers/heatmap.py` (prefix `/api/v1/analytics/campaigns`), `mvp.py`, `timeline.py`. Each file uses the same prefix.
- The owner has no summary route. The summary route either moves to the owner or is removed. Choose in the PR, and record the reason.
- ADR-0006: campaign analytics reads Redis Streams events. The gateway does not read streams.
- Telemetry data flow: the owner's read models are in memory until the owner's own fix (`w2-campaign-analytics.md` F5). This task does not fix that.

## Product & User Story References
- [`prd-0012-campaign-telemetry-and-living-chronicle-timeline.md`](../../product/accepted/prd-0012-campaign-telemetry-and-living-chronicle-timeline.md)
- [`us-0040-campaign-combat-telemetry-and-living-timeline.md`](../../user_stories/accepted/us-0040-campaign-combat-telemetry-and-living-timeline.md)
- [`us-0054-combat-spatial-heatmaps-and-party-damage-analytics.md`](../../user_stories/accepted/us-0054-combat-spatial-heatmaps-and-party-damage-analytics.md)

## Detailed Specification & Implementation Plan
1. Create `gateway/api/src/gateway_api/routers/analytics_views.py`. Expose:
   - `GET /api/v1/analytics/campaigns/{campaign_id}/heatmap`
   - `GET /api/v1/analytics/campaigns/{campaign_id}/mvp`
   - `GET /api/v1/analytics/campaigns/{campaign_id}/timeline`
   - `GET /api/v1/analytics/campaigns/{campaign_id}` (summary), only if the owner route exists after the PR, otherwise remove it.
   Each handler forwards through `ServiceClient` and passes the caller identity.
2. Forward the query parameters `cell_size`, `metric` and `limit` to the owner. Verify names against the owner.
3. Delete `hub_views.py`, its fallback helper and its payloads. Remove the import in `main.py`.
4. If the summary route is added to the owner, put it in its own router file in `services/campaign_analytics`.
5. Replace `CAMPAIGN_ANALYTICS_URL` with the `ServiceClient` settings field from TASK-0580.
6. Update `docs/reference/ports-and-endpoints.md` rows at lines 227-249.

## Frontdoor Blackbox Test Plan
Test file: `gateway/api/tests/test_blackbox_gateway_analytics_views.py`. `campaign_analytics` runs as an ASGI app. Setup: post combat telemetry through the owner's public ingestion route, or through the Redis Streams publish path the service uses.

| Case | Expected before fix | Expected after fix |
|---|---|---|
| Heatmap for a campaign with no telemetry returns an empty grid from the owner | Fails: canned cells | Passes |
| MVP returns the owner's MVP for the recorded encounter | Fails: canned "Valeros" | Passes |
| Owner 403 passes through | Fails: canned 200 | Passes |
| Owner down returns 503 | Fails: canned 200 | Passes |

The test must not assert "Valeros", "session-tomb-14", "enc-crypt-1" or 42 turns.

## Definition of Done
1. `hub_views.py` is removed. `rg "total_combat_turns|Valeros|Breach of the Astral" gateway/api/src` returns nothing.
2. The three proxy routes and the summary decision are implemented.
3. Each proxy forwards through `ServiceClient`.
4. The blackbox test file passes. `uv run ruff check .` passes.
5. `docs/reference/ports-and-endpoints.md` matches the routes.

## Audit Provenance

- Severity: high
- Source audits: `w2-campaign-analytics.md`, `w1-gateway-api.md`, `w1-gates-infra.md`
