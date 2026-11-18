---
id: '0585'
title: Gateway Character Core Routes Proxy to Character Sheet
status: Complete
created: 2026-11-17
dependencies:
- TASK-0580
governing_adrs:
- ADR-0001
- ADR-0007
- ADR-0011
governing_prds:
- PRD-0006
governing_stories:
- US-0064
- US-0015
target_release: 0.9.0
---

# TASK-0585: Gateway Character Core Routes Proxy to Character Sheet

## Status
Complete

## Summary
Character create, list, read and campaign assignment are served from the gateway's in-memory `CharacterStore`. Move them to `character_sheet`. The gateway forwards each call. The store and the mutation sync code are deleted. `character_sheet` gets a roster list route, which it lacks today.

## Problem Statement
- `gateway/api/src/gateway_api/character_store.py:18-30` (removed) holds characters in a `dict`. `routers/characters.py:20-40` serves list and create from it. `routers/characters.py` also serves `PATCH .../campaign` and `DELETE` (`w1-character-sheet.md` F1).
- `character_store_mutations.py:26-50` imports `character_sheet.dependencies` and writes the aggregate in-process. It swallows errors with `except Exception: pass` (`w1-gateway-api.md` F10, `w1-character-sheet.md` F7).
- The owner has `POST /api/v1/characters`, `POST /api/v1/characters/create`, `GET /api/v1/characters/{character_id}` (`services/character_sheet/src/character_sheet/router.py:16-71`), and `PATCH .../campaign` in the same family. There is no `GET /api/v1/characters` list route.
- `DELETE /api/v1/characters/{id}` has no owner route.

## Documentation & Architecture Review
- ADR-0011: the character aggregate is changed only through `character_sheet`. The gateway must not import the aggregate.
- `docs/how-to/interact-with-character-sheet-and-inventory.md` describes the character flows. Check it before writing the list route.
- `docs/reference/events-schema.md` lists character events. Do not change event names in this task.
- Ownership of a character (the `character:<id>#owner` tuple) is written by the authorization theme. This task keeps the existing tuple writes where they are, and moves each write into the owner in the same change if the write is in the gateway.

## Product & User Story References
- [`prd-0006-digital-character-sheet-inventory-and-conditions.md`](../../product/accepted/prd-0006-digital-character-sheet-inventory-and-conditions.md)
- [`us-0064-character-roster-management-and-party-assignment.md`](../../user_stories/accepted/us-0064-character-roster-management-and-party-assignment.md)
- [`us-0015-character-inventory-equipment-tracking.md`](../../user_stories/accepted/us-0015-character-inventory-equipment-tracking.md)

## Detailed Specification & Implementation Plan
1. Add `GET /api/v1/characters` to `services/character_sheet`. It lists the characters the caller may view. Use a SpiceDB lookup through the shared permission helper. Return the same fields as `GET /api/v1/characters/{id}`. Keep the file under 300 lines.
2. Add `DELETE /api/v1/characters/{character_id}` to `character_sheet`, or remove the gateway route if the user stories do not need it. Record the choice in the PR.
3. Create `gateway/api/src/gateway_api/routers/characters_proxy.py`. Forward `GET` list, `POST` create, `GET` read and `PATCH .../campaign` through `ServiceClient`. Pass the caller identity.
4. Delete `routers/characters.py`, `character_store.py`, `character_store_mutations.py` and the `DEFAULT_CHARACTERS` seed data. Remove the `character_sheet` import from the gateway.
5. Update `docs/reference/ports-and-endpoints.md` (the `character_sheet` row and the gateway rows at lines 250-260).

## Frontdoor Blackbox Test Plan
Test file: `tests/test_blackbox_gateway_character_proxy.py`. `character_sheet` runs as an ASGI app. Setup: create characters with `POST /api/v1/characters` through the gateway.

| Case | Expected before fix | Expected after fix |
|---|---|---|
| Created character appears in `GET /api/v1/characters` after a gateway restart | Fails: store lost | Passes |
| `PATCH .../campaign` then GET shows the campaign | Fails: store only | Passes |
| Character owned by another user is not listed | Fails: all listed | Passes |
| Owner down returns 503 on create | Fails: 200 from store | Passes |
| `rg "CharacterStore" gateway/api` | Fails: matches | Passes: no match |

Restart test: build the gateway app twice with the same owner ASGI app. The second app must still return the character.

## Definition of Done
1. `character_store.py`, `character_store_mutations.py` and `routers/characters.py` are removed.
2. `character_sheet` has the list route and the delete decision is implemented.
3. The gateway imports nothing from `character_sheet`.
4. The blackbox test file passes. `uv run ruff check .` passes.
5. `docs/reference/ports-and-endpoints.md` matches the routes.

## Audit Provenance

- Severity: critical
- Source audits: `w1-character-sheet.md`, `w1-gateway-api.md`, `w3-ddd-architecture.md`
