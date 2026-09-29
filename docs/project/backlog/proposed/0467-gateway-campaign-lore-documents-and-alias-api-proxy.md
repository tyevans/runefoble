---
id: '0467'
title: Gateway Campaign Lore Documents and Alias API Routing & Zanzibar Proxy
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0008
- TASK-0047
- TASK-0208
governing_adrs:
- ADR-0001
- ADR-0005
- ADR-0007
governing_prds:
- PRD-0007
governing_stories:
- US-0036
- US-0063
target_release: 0.9.0
---

# TASK-0467: Gateway Campaign Lore Documents and Alias API Routing & Zanzibar Proxy

## Status
Proposed

## Summary
Implement public Gateway API proxy endpoints for worldbuilding lore document ingestion (`POST /api/v1/campaigns/{campaign_id}/lore/documents`), document listing/detail retrieval (`GET /api/v1/campaigns/{campaign_id}/lore/documents`), and entity alias consolidation (`POST /api/v1/campaigns/{campaign_id}/lore/aliases/consolidate`) in `gateway/api/src/gateway_api/routers/lore.py`. Enforce SpiceDB Zanzibar object authorization ensuring only users with `edit` or `manage` permission on the campaign can ingest lore or merge aliases, while users with `view` permission can access non-secret documents.

## Problem Statement
While `services/campaign_lore` contains document ingestion and alias consolidation endpoints, they are currently internal and not exposed through the unified Gateway API (`gateway/api`). Frontdoor clients and the App Shell cannot upload lore documents, manage secrecy flags, or consolidate character aliases through public gateway routes. Furthermore, lack of Gateway Zanzibar checks leaves lore mutations unprotected from unauthorized player role tampering.

## Governing Architecture & ADRs
- **ADR-0001: Google Zanzibar for Fine-Grained Authorization**: Protect ingestion and consolidation routes with `require_zanzibar_permission("manage", "campaign", "campaign_id")` and `require_zanzibar_permission("view", "campaign", "campaign_id")`.
- **ADR-0005: Zitadel for Authentication & Identity**: Secure routes with JWT bearer token validation and user identity propagation.
- **ADR-0007: Domain-Driven Design Architecture**: Keep gateway logic focused on HTTP proxying, authorization checks, and graceful fallbacks without leaking internal service models.

## Product & User Story References
- [`prd-0007-campaign-worldbuilding-lore-and-rag-engine.md`](../../product/accepted/prd-0007-campaign-worldbuilding-lore-and-rag-engine.md)
- [`us-0036-rag-indexed-campaign-worldbuilding-lore.md`](../../user_stories/accepted/us-0036-rag-indexed-campaign-worldbuilding-lore.md)
- [`us-0063-campaign-creation-dashboard-and-zanzibar-roles.md`](../../user_stories/accepted/us-0063-campaign-creation-dashboard-and-zanzibar-roles.md)


## Scope of Work
1. **Gateway Lore Router Implementation (`gateway/api/src/gateway_api/routers/lore.py`)**:
   - `POST /api/v1/campaigns/{campaign_id}/lore/documents`: Ingest markdown/text lore documents with `is_secret` flag, tags, and optional aliases. Protected with `require_zanzibar_permission("manage", "campaign", "campaign_id")`.
   - `GET /api/v1/campaigns/{campaign_id}/lore/documents`: List campaign documents with filter by secrecy. Protected with `require_zanzibar_permission("view", "campaign", "campaign_id")`. Automatically filters out `is_secret=True` documents unless user has `manage` permission.
   - `POST /api/v1/campaigns/{campaign_id}/lore/aliases/consolidate`: Merge alias titles into canonical entity nodes. Protected with `require_zanzibar_permission("manage", "campaign", "campaign_id")`.
   - `GET /api/v1/campaigns/{campaign_id}/lore/aliases/resolve`: Resolve alias names to canonical nodes. Protected with `require_zanzibar_permission("view", "campaign", "campaign_id")`.
2. **Gateway App Integration (`gateway/api/src/gateway_api/main.py`)**:
   - Register the new `lore.py` router on the FastAPI application instance.
   - Include router in OpenAPI documentation aggregation.
3. **Graceful Fallbacks & Offline Stubs**:
   - Provide deterministic fallback structures for local offline development when `campaign-lore` service is unreachable.

## Definition of Done
1. `gateway/api/src/gateway_api/routers/lore.py` created and strictly < 150 lines per Hard Invariant 6.
2. Endpoints enforce Zanzibar `manage` and `view` permissions correctly using `require_zanzibar_permission`.
3. Players cannot access `is_secret=True` lore documents via the Gateway API.
4. Route integration tests implemented in `gateway/api/tests/` asserting HTTP 200/201 and HTTP 403 authorization failures.
5. All code passes `uv run ruff check .` and `uv run ruff format --check .`.
