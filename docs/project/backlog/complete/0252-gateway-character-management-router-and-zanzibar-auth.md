---
id: '0252'
title: Gateway Character Management Router and Zanzibar Authorization
status: Complete
created: 2026-09-27
dependencies:
- TASK-0208
- TASK-0211
governing_adrs:
- ADR-0001
- ADR-0005
- ADR-0007
governing_prds:
- PRD-0006
- PRD-0023
governing_stories:
- US-0064
- US-0069
target_release: 0.8.0
pr_url: https://github.com/tyevans/runefoble/pull/284
---
# TASK-0252: Gateway Character Management Router and Zanzibar Authorization

## Status
Refined

## Summary
Create `gateway/api/src/gateway_api/routers/characters.py` and register it in `gateway/api/src/gateway_api/main.py`. Expose REST endpoints: `GET /api/v1/characters` (list user-owned characters), `POST /api/v1/characters` (create character and write SpiceDB owner tuple), `GET /api/v1/characters/{id}` (fetch character with view permission), `PATCH /api/v1/characters/{id}/campaign` (assign/unassign character to campaign with edit permission), and `DELETE /api/v1/characters/{id}` (delete owned character).

## Problem Statement
The frontend Character Roster (`<runefoble-character-roster>`) calls `GET /api/v1/characters`, but the Gateway API returns HTTP 404 because no character router exists in `gateway/api/src/gateway_api/routers/`. As a result, the frontend always falls back to static dummy characters. Furthermore, when users attempt to create characters, assign them to campaigns, or delete them, there are no endpoints to accept the payloads, validate SpiceDB Zanzibar permissions, or write relationship tuples.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/define-spicedb-zanzibar-permissions.md`: Character schema definition (`character:id#owner@user:id`, `character:id#campaign@campaign:id`).
  - `docs/reference/ports-and-endpoints.md`: Gateway router registration and OpenAPI hub.
  - `docs/explanation/zanzibar-in-ttrpg.md`: Zanzibar permissions for player characters.
- **Governing Architecture & ADRs**:
  - **ADR-0001: SpiceDB Zanzibar Object Authorization**: Enforcing `owner` and `view` permissions on character resources.
  - **ADR-0005: Kubernetes-First Infrastructure with Helm and Kind**: FastAPI gateway service.
  - **ADR-0007: Domain-Driven Design Architecture**: Clean boundaries between Gateway and character services.

## Product & User Story References
- **Product Requirement**: [`prd-0006-digital-character-sheet-inventory-and-conditions.md`](../../product/accepted/prd-0006-digital-character-sheet-inventory-and-conditions.md), [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
- **User Stories**:
  - [`us-0064-character-roster-management-and-party-assignment.md`](../../user_stories/accepted/us-0064-character-roster-management-and-party-assignment.md)
  - [`us-0069-character-sheet-inspector-and-active-session-binding.md`](../../user_stories/accepted/us-0069-character-sheet-inspector-and-active-session-binding.md)

## Detailed Specification & Implementation Plan
1. **Character Store & Models (`gateway/api/src/gateway_api/character_store.py`)**:
   - Define `CharacterRecord` storing `id`, `name`, `character_class`, `subclass`, `level`, `current_hp`, `max_hp`, `armor_class`, `speed`, `campaign_id`, `owner_id`, `portrait_url`.
   - Provide in-memory storage with initial default characters for dev/testing.
   - Implement `create_character()`, `get_character()`, `list_characters_for_user()`, `assign_campaign()`, and `delete_character()`.
2. **Gateway Router (`gateway/api/src/gateway_api/routers/characters.py`)**:
   - `GET /api/v1/characters`: Query all characters where `user` has `view` or `owner` relation in SpiceDB.
   - `POST /api/v1/characters`: Validate request, generate ID, save record, write `character:<id>#owner@user:<user_id>` in SpiceDB.
   - `GET /api/v1/characters/{character_id}`: Check Zanzibar `view` permission on `character:<id>`, return character details.
   - `PATCH /api/v1/characters/{character_id}/campaign`: Check Zanzibar `edit` permission, update `campaign_id`, write/delete `character:<id>#campaign@campaign:<campaign_id>` tuple.
   - `DELETE /api/v1/characters/{character_id}`: Check Zanzibar `owner` permission, remove character and delete relationships.
3. **App Integration (`gateway/api/src/gateway_api/main.py`)**:
   - Include `characters_router` in `app.include_router(characters_router)`.
4. **File Length Safety**:
   - Keep `characters.py` <200 lines and `character_store.py` <250 lines.

## Definition of Done
- [ ] `GET /api/v1/characters` returns 200 with list of user-owned characters.
- [ ] `POST /api/v1/characters` returns 201 Created and writes SpiceDB owner tuple.
- [ ] `PATCH /api/v1/characters/{id}/campaign` updates campaign linkage and writes SpiceDB campaign tuple.
- [ ] Non-owners cannot edit or delete characters (returns 403 Forbidden).
- [ ] All source files remain strictly <500 lines.
