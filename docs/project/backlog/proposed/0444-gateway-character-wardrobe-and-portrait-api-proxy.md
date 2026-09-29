---
id: '0444'
title: Gateway Character Wardrobe and Dynamic Portrait API Routing & Zanzibar Proxy
status: Proposed
created: 2026-09-29
dependencies:
- TASK-0124
- TASK-0252
- TASK-0356
governing_adrs:
- ADR-0001
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0006
- PRD-0016
- PRD-0023
governing_stories:
- US-0055
- US-0064
- US-0069
target_release: 0.9.0
---

# TASK-0444: Gateway Character Wardrobe and Dynamic Portrait API Routing & Zanzibar Proxy

## Status
Proposed

## Summary
Implement dedicated Gateway APIRouter endpoints (`GET /api/v1/characters/{character_id}/wardrobe`, `POST /api/v1/characters/{character_id}/wardrobe`, and `POST /api/v1/characters/{character_id}/portrait`) protected by SpiceDB Zanzibar authorization (`view` or `edit` permission on `character:{character_id}`) proxying downstream to the Character Sheet service (`wardrobe_router.py`), with in-memory fallback support in `character_store`, enabling clients to query unlocked wardrobe variants, register synthesized attire variations, and update character portraits through the public Gateway frontdoor.

## Problem Statement
While `services/character_sheet/src/character_sheet/wardrobe_router.py` exposes REST endpoints for wardrobe attire variants and portrait updates per PRD-0016 and US-0055, the unified Gateway API (`gateway/api/src/gateway_api/`) lacks route mappings for `/api/v1/characters/{id}/wardrobe` and `/api/v1/characters/{id}/portrait`. Consequently, frontend clients and external consumers receive 404 Not Found when attempting to access wardrobe attire or update character portrait avatars via the Gateway frontdoor. Furthermore, SpiceDB Zanzibar object-level permissions (`view` for read, `edit` for mutations) are not enforced at the gateway layer for wardrobe subresources.

## Governing Architecture & ADRs
- **ADR-0001: Google Zanzibar for Fine-Grained Authorization**: Enforce `view` permission on GET queries and `edit` permission on POST mutations for `character:{character_id}`.
- **ADR-0007: Domain-Driven Design Architecture**: Maintain bounded context boundaries between Gateway API routing and Character Sheet domain state.
- **ADR-0013: Frontend Microfrontend Architecture**: Provide consistent frontdoor REST interfaces for UI components.

## Product & User Story References
- [`prd-0016-character-leitmotifs-and-kinetic-spell-vfx.md`](../../product/accepted/prd-0016-character-leitmotifs-and-kinetic-spell-vfx.md)
- [`prd-0006-digital-character-sheet-inventory-and-conditions.md`](../../product/accepted/prd-0006-digital-character-sheet-inventory-and-conditions.md)
- [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- [`us-0055-dynamic-character-wardrobe-and-condition-portraits.md`](../../user_stories/accepted/us-0055-dynamic-character-wardrobe-and-condition-portraits.md)
- [`us-0064-character-roster-and-party-assignment.md`](../../user_stories/accepted/us-0064-character-roster-and-party-assignment.md)

## Scope of Work
1. **Gateway Models & Schemas (`gateway/api/src/gateway_api/character_models.py`)**:
   - Define `WardrobeVariantResponse`, `AddWardrobeVariantRequest`, and `UpdatePortraitRequest` Pydantic models matching character sheet domain schemas (< 50 lines).
2. **Gateway In-Memory Store Extension (`gateway/api/src/gateway_api/character_store.py`)**:
   - Add wardrobe variant tracking (`wardrobe_variants: dict[str, dict[str, Any]]`) and portrait updating methods to `CharacterStore` for local development and test fallbacks (< 60 lines).
3. **Gateway Subresource Router Endpoints (`gateway/api/src/gateway_api/routers/character_subresources.py` or `characters/wardrobe.py`)**:
   - Add `GET /api/v1/characters/{character_id}/wardrobe` with `Depends(require_zanzibar_permission("view", "character", "character_id"))`.
   - Add `POST /api/v1/characters/{character_id}/wardrobe` with `Depends(require_zanzibar_permission("edit", "character", "character_id"))`.
   - Add `POST /api/v1/characters/{character_id}/portrait` with `Depends(require_zanzibar_permission("edit", "character", "character_id"))`.
   - Proxy requests downstream to `CHARACTER_SHEET_URL` via `proxy_or_fallback()`.
4. **Verification**:
   - Add blackbox frontdoor tests verifying wardrobe variant creation, listing, portrait switching, and 403 Zanzibar rejection for unauthorized callers.

## Definition of Done
1. All three wardrobe and portrait endpoints exposed under `/api/v1/characters/{character_id}/...`.
2. SpiceDB Zanzibar permissions strictly enforced (403 Forbidden when caller lacks `view`/`edit`).
3. Downstream proxying works with live character_sheet service, and fallback memory store handles standalone gateway runs.
4. Comprehensive blackbox tests pass with 100% assertions.
5. All modified files adhere to Hard Invariant 6 (< 500 lines).
