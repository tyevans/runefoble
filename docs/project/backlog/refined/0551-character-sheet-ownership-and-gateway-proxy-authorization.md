---
id: '0551'
title: Character Sheet Ownership and Gateway Character Proxy Authorization
status: Refined
created: 2026-11-17
dependencies:
- TASK-0520
- TASK-0541
- TASK-0542
- TASK-0540
- TASK-0528
- TASK-0536
governing_adrs:
- ADR-0001
- ADR-0007
- ADR-0014
governing_prds:
- PRD-0006
governing_stories:
- US-0069
- US-0015
- US-0051
- US-0055
target_release: 0.9.0
severity: critical
source_audits:
- w1-character-sheet.md
- w3-authz-coverage.md
- w1-gateway-api.md
---

# TASK-0551: Character Sheet Ownership and Gateway Character Proxy Authorization

## Status
Refined

## Summary
Most mutating character routes have no check. The few that have one run it only when an identity header is present. Character creation writes the `owner` tuple inside `contextlib.suppress`, so a failed write still returns success. The gateway character sub-resource proxy forwards no identity and falls back to an in-memory store. This task applies one permission rule to every character route, makes ownership writes fail loudly, and removes the gateway fallback. Persistence of character state is owned by TASK-0444, and this task does not change it.

## Problem Statement
- `services/character_sheet/src/character_sheet/router.py`: `POST /api/v1/characters` (line 18, and `/create`), `level-up` (40), `spells/prepare` (50), `spells/cast` (65), `health` (77), `penalties` (87, 97), `inventory` (103, 109), `equipment` (115, 120), `conditions` (125, 130): no check (`w1-character-sheet.md` F2, `w3-authz-coverage.md` rows 143-158). Probe: a non-owner penalty returns 200.
- `services/character_sheet/src/character_sheet/dependencies.py` `authorize_character_edit`: runs the check only `if user_id and ...`. A request with no header passes. Used by `PUT guardrails` (router 136), `PATCH campaign` (156), wardrobe (`wardrobe_router.py:49,79`), and crafting combine (`crafting_router.py:86`). Probe: anonymous `PUT guardrails` returns 200.
- `router.py:27,32`: ownership tuple writes are inside `contextlib.suppress(Exception)`. A failed `owner` write returns success.
- `GET /api/v1/characters/{id}`: no `character.view` check.
- `gateway/api/src/gateway_api/routers/character_subresources.py:26,36-48`: proxies to `CHARACTER_SHEET_URL`, which Helm does not set. On any error it falls back to in-memory state and forwards no identity (`w1-gateway-api.md` F9, `w3-authz-coverage.md` F20).
- `gateway/api/src/gateway_api/routers/characters.py:118` (`DELETE /api/v1/characters/{id}`) checks `owner`, which is a relation, not a permission (`w3-authz-coverage.md` F16). The schema now has `character.delete` (TASK-0540).

## Documentation & Architecture Review
- ADR-0001: `character.edit` for mutations, `character.view` for reads, `character.delete` for deletion. Owner and DM share `edit` through the schema (`owner + campaign->run_session`).
- ADR-0007: the character context owns character state. The gateway routes requests and forwards the verified principal. The gateway does not hold character state (`w3-ddd-architecture.md` F5).
- TASK-0444 (refined) describes an in-memory fallback for the wardrobe and portrait routes in `character_store`. That conflicts with Hard Invariant 2 and with TASK-0536, which removes proxy fallbacks. The index report records the correction. This task does not depend on TASK-0444.
- `docs/reference/events-schema.md` lists character events. It is updated by the persistence task.
- `docs/how-to/interact-with-character-sheet-and-inventory.md` describes these routes. Update the auth text.

## Product & User Story References
- US-0069 (character inspector and session binding). US-0015 (inventory and equipment). US-0051 (level progression and spellbook). US-0055 (wardrobe and condition portraits). PRD-0006 (character sheet).

## Detailed Specification & Implementation Plan
1. One FastAPI dependency `require_character_permission(permission)` in `character_sheet/dependencies.py`. It reads the verified principal that TASK-0528 provides. It calls `check_permission("character", id, permission, "user", principal)`. It returns 401 for a missing principal, 403 for denial, and 503 for `AuthzUnavailableError`.
2. Apply the dependency to every route in step "Problem Statement":
   - Reads (`GET`): `character.view`.
   - Mutations: `character.edit`.
   - Gateway `DELETE /api/v1/characters/{id}`: `character.delete`.
3. Creation: after the character is saved, write `character:<id>#owner@user:<principal>` and `character:<id>#campaign@campaign:<cid>` (when a campaign is given). The write is not suppressed. A failed write returns 503 and the character is not returned as created. Use the write-ahead order that the aggregate supports (the save and the tuple write are one operation from the caller's view).
4. Delete `authorize_character_edit` and its `if user_id` branch. Replace callers with the new dependency.
5. Gateway sub-resource proxy (`character_subresources.py`): TASK-0536 forwards the bearer token and returns 502 on upstream failure. That change removes the in-memory fallback. This task does not repeat it.
6. Gateway `characters.py`: the create route writes the owner tuple through the library factory. The `owner` check on delete moves to `character.delete`.

## Frontdoor Blackbox Test Plan
Setup: a character is created through `POST /api/v1/characters`. The owner is the principal that created it. A second player joins the campaign through invite. The DM uses the role route.
- Before the fix, anonymous `PUT /api/v1/characters/{id}/guardrails` returns 200. After the fix it returns 401.
- A non-owner player calls `POST .../penalties`: 403. The DM with `run_session` on the character's campaign: 200.
- A non-owner calls `POST .../health`: 403. The owner: 200.
- `GET /api/v1/characters/{id}` by a non-member: 403.
- A character creation where the stubbed SpiceDB write fails returns 503 and no character is listed. Before the fix it returns 200.
- `DELETE /api/v1/characters/{id}` by the DM (not owner): 403. By the owner: 204.
- Gateway sub-resource request with the proxy target unreachable: 502. Before the fix it returns 200 from memory.

## Definition of Done
1. Frontdoor tests exist in `tests/test_blackbox_character_authz.py` and pass against the live harness.
2. No `contextlib.suppress` wraps a permission write in `services/character_sheet/` or in `gateway/api/src/gateway_api/routers/characters.py`.
3. `character_subresources.py` contains no in-memory fallback.
4. `docs/how-to/interact-with-character-sheet-and-inventory.md` is updated.
5. `uv run pytest services/character_sheet gateway/api` passes for the changed tests. `uv run ruff check` passes for both packages.
6. No file in the change exceeds 500 lines. `router.py` is split by route group if it grows past the limit.
