---
id: '0451'
title: Gateway West Marches and Caravan API Routing & Zanzibar Proxy
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0127
- TASK-0129
- TASK-0164
- TASK-0165
governing_adrs:
- ADR-0001
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0018
- PRD-0023
governing_stories:
- US-0058
- US-0050
- US-0063
target_release: 0.9.0
---

# TASK-0451: Gateway West Marches and Caravan API Routing & Zanzibar Proxy

## Status
Proposed

## Summary
Implement dedicated Gateway APIRouter endpoints (`/api/v1/west_marches/...` and `/api/v1/caravan/...`) protected by SpiceDB Zanzibar authorization (`view` and `contribute` permissions on `universe:{universe_id}` and `campaign:{campaign_id}`) proxying downstream to the Campaign Lore (`west_marches.py`) and Game Session (`caravan_trade.py`, `caravan_contracts/`) microservices, with in-memory fallback support in gateway stores, enabling frontend clients to query shared frontier discoveries, dispatch caravans, and post/claim mercenary bounties through the public Gateway frontdoor.

## Problem Statement
While `services/campaign_lore/src/campaign_lore/routers/west_marches.py` and `services/game_session/src/game_session/routers/caravan_contracts/` expose internal REST endpoints for West Marches discoveries, stronghold upgrades, and caravan trade routes per PRD-0018 and US-0058, the unified Gateway API (`gateway/api/src/gateway_api/`) lacks route mappings for these domains. Consequently, external clients and the frontend App Shell cannot query shared world state, dispatch cross-campaign trade caravans, or claim mercenary bounties via the public Gateway frontdoor. Furthermore, SpiceDB Zanzibar object-level multi-campaign permissions (`view` for world inspection, `contribute` for discoveries, outposts, and contract claims) are not enforced at the gateway perimeter.

## Governing Architecture & ADRs
- **ADR-0001: Google Zanzibar for Fine-Grained Authorization**: Enforce `view` permission on GET queries and `contribute` or `admin` permissions on POST mutations for `universe:{universe_id}` or linked `campaign:{campaign_id}`.
- **ADR-0007: Domain-Driven Design Architecture**: Maintain clean service boundaries between Gateway API routing and underlying Campaign Lore / Game Session aggregates.
- **ADR-0013: Frontend Microfrontend Architecture**: Expose standard REST endpoints consumable by App Shell microfrontends without direct backend coupling.

## Product & User Story References
- [`prd-0018-west-marches-shared-world-state-and-cross-campaign-trade.md`](../../product/accepted/prd-0018-west-marches-shared-world-state-and-cross-campaign-trade.md)
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`us-0058-west-marches-shared-world-state-and-caravan-trade.md`](../../user_stories/accepted/us-0058-west-marches-shared-world-state-and-caravan-trade.md)
- [`us-0050-collaborative-campaign-atlas-and-living-codex.md`](../../user_stories/accepted/us-0050-collaborative-campaign-atlas-and-living-codex.md)

## Scope of Work
1. **Gateway Models & Schemas (`gateway/api/src/gateway_api/west_marches_models.py`)**:
   - Define Pydantic request and response schemas for discoveries, outposts, notices, stronghold upgrade contributions, caravan trade dispatches, and bounty contracts (< 120 lines).
2. **Gateway In-Memory Store Extension (`gateway/api/src/gateway_api/west_marches_store.py`)**:
   - Implement lightweight in-memory storage for universes, shared discovery pins, caravan transit schedules, and contract escrow ledgers for local development and test fallbacks (< 140 lines).
3. **Gateway Router Endpoints (`gateway/api/src/gateway_api/routers/west_marches.py`)**:
   - Implement `GET /api/v1/west_marches/{universe_id}` with `Depends(require_zanzibar_permission("view", "universe", "universe_id"))`.
   - Implement `POST /api/v1/west_marches/{universe_id}/discoveries` with `Depends(require_zanzibar_permission("contribute", "universe", "universe_id"))`.
   - Implement `POST /api/v1/west_marches/{universe_id}/strongholds/{facility_id}/upgrade`.
   - Implement `GET /api/v1/caravan/contracts/{universe_id}` and `POST /api/v1/caravan/contracts/{universe_id}`.
   - Implement `POST /api/v1/caravan/contracts/{contract_id}/claim` and `POST /api/v1/caravan/contracts/{contract_id}/fulfill`.
   - Implement `POST /api/v1/caravan/trade/dispatch` and `GET /api/v1/caravan/trade/routes/{universe_id}`.
   - Route downstream calls via `proxy_or_fallback()` to `CAMPAIGN_LORE_URL` and `GAME_SESSION_URL`.
4. **App Integration**:
   - Register the router in `gateway/api/src/gateway_api/app.py`.
5. **Verification**:
   - Add blackbox frontdoor tests in `tests/test_blackbox_gateway_west_marches.py` verifying discovery submission, caravan trade dispatch, bounty contract claiming, and 403 Forbidden for unlinked campaign callers.

## Definition of Done
1. All West Marches and Caravan endpoints exposed under `/api/v1/west_marches/...` and `/api/v1/caravan/...`.
2. SpiceDB Zanzibar permissions strictly enforced (403 Forbidden when caller lacks `view`/`contribute`).
3. Downstream proxying operational with microservices, and fallback memory store handles isolated testing.
4. Comprehensive blackbox tests pass with 100% assertions.
5. All modified files adhere to Hard Invariant 6 (< 500 lines).
