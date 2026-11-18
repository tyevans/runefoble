---
id: '0587'
title: Gateway Campaign Lore Hub Views Proxy to Campaign Lore
status: Refined
created: 2026-11-17
dependencies:
- TASK-0580
governing_adrs:
- ADR-0001
- ADR-0007
governing_prds:
- PRD-0007
- PRD-0023
governing_stories:
- US-0050
- US-0036
target_release: 0.9.0
---

# TASK-0587: Gateway Campaign Lore Hub Views Proxy to Campaign Lore

## Status
Refined

## Summary
The atlas and codex routes in `gateway/api/src/gateway_api/routers/hub_views.py` return canned pins and entries when campaign-lore fails. They also drop the caller identity. Move the lore views into a new `lore_views.py` that proxies to `campaign_lore`. Forward the identity. Delete the canned data. The analytics views stay in `hub_views.py` until TASK-0588.

## Problem Statement
- `hub_views.py:16-25` (`_proxy_or_fallback`) catches every exception and returns fallback data. A real campaign with a failed lore service sees "Sunken Citadel" and "Star-Eater Relic" (`w2-campaign-lore.md` F14, `w1-gates-infra.md` F7).
- `hub_views.py:18` sends no headers. Campaign-lore sees every gateway call as anonymous, so `party_shared` codex notes are hidden from members (`w2-campaign-lore.md` F14).
- The fallback shape for codex is `{"entries": ...}`. The real route returns a bare list.
- Only three GET routes are proxied. The rest of campaign-lore is out of this task. TASK-0467 covers documents and aliases.

## Documentation & Architecture Review
- Owner routes exist in `services/campaign_lore/src/campaign_lore/routers/`: atlas (`APIRouter(prefix="/api/v1/campaigns/{campaign_id}/atlas")`), codex (`prefix="/api/v1/campaigns/{campaign_id}/codex"`), and the codex entries list.
- `docs/reference/ports-and-endpoints.md:176-186` lists the owner routes.
- The atlas and codex privacy checks are the owner's job (SpiceDB, secret lore). The gateway must forward the identity and must not filter the response.
- The `CAMPAIGN_LORE_URL` default (`:8006`) is set by TASK-0624 in Helm. Remove the code default.

## Product & User Story References
- [`prd-0007-campaign-worldbuilding-lore-and-rag-engine.md`](../../product/accepted/prd-0007-campaign-worldbuilding-lore-and-rag-engine.md)
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`us-0050-collaborative-campaign-atlas-and-living-codex.md`](../../user_stories/accepted/us-0050-collaborative-campaign-atlas-and-living-codex.md)

## Detailed Specification & Implementation Plan
1. Create `gateway/api/src/gateway_api/routers/lore_views.py`. Expose:
   - `GET /api/v1/campaigns/{campaign_id}/atlas`
   - `GET /api/v1/campaigns/{campaign_id}/codex`
   - `GET /api/v1/campaigns/{campaign_id}/codex/entries`
   Each handler forwards through `ServiceClient` (TASK-0580) and passes the caller identity.
2. Pass the query parameters (`era`, `tag`, `search`) through. Verify each name against the owner router.
3. Remove the three lore routes and the lore fallback payloads from `hub_views.py`. Leave the analytics routes in place for TASK-0588.
4. Mount the new router in `main.py` where the lore routes were mounted.
5. Update `docs/reference/ports-and-endpoints.md` for the three gateway rows.

## Frontdoor Blackbox Test Plan
Test file: `tests/test_blackbox_gateway_lore_views.py`. `campaign_lore` runs as an ASGI app. Setup: create a pin and a codex entry through the owner's public routes (`POST .../atlas/pins`, `POST .../codex/entries`).

| Case | Expected before fix | Expected after fix |
|---|---|---|
| Atlas GET returns the pin created through the owner | Fails: "Sunken Citadel" canned | Passes |
| Party-shared codex entry is visible to a member and hidden from an outsider | Fails: anonymous for all | Passes |
| Owner down returns 503 | Fails: canned 200 | Passes |
| Owner 403 passes through | Fails: canned 200 | Passes |

The test must not assert the strings "Sunken Citadel" or "Star-Eater Relic".

## Definition of Done
1. `rg "Sunken Citadel|Star-Eater Relic" gateway/api/src` returns nothing.
2. `lore_views.py` forwards the identity and uses `ServiceClient`.
3. The blackbox test file passes. `uv run ruff check .` passes.
4. `docs/reference/ports-and-endpoints.md` matches the routes.

## Orchestrator Addenda (2026-11-17, round 2)

Source: `.audit/synth/discovered-round2.md`.

- Add gateway proxies for the lore write routes (POST atlas pins and POST codex entries). Use the write permission from runefoble.zed, not the view permission.

## Audit Provenance

- Severity: high
- Source audits: `w2-campaign-lore.md`, `w1-gateway-api.md`, `w1-gates-infra.md`
