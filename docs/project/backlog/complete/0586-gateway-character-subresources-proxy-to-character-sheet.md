---
id: '0586'
title: Gateway Character Subresource Routes Proxy to Character Sheet
status: Complete
created: 2026-11-17
dependencies:
- TASK-0585
governing_adrs:
- ADR-0001
- ADR-0007
- ADR-0011
governing_prds:
- PRD-0006
- PRD-0016
governing_stories:
- US-0015
- US-0051
- US-0069
target_release: 0.9.0
---

# TASK-0586: Gateway Character Subresource Routes Proxy to Character Sheet

## Status
Complete

## Summary
`character_subresources.py` (356 lines) holds health, equipment, inventory, conditions, spells and guardrails. Each handler proxies only when `CHARACTER_SHEET_URL` is set. The env var is set nowhere, so the in-memory path always runs. Replace every handler with a pure proxy. Delete the fallback and the in-memory mutations. This task replaces TASK-0435 (decomposition), because pure proxies need no decomposition.

## Problem Statement
- `character_subresources.py:36-49` (`proxy_or_fallback`) returns the in-memory result when the URL is unset, when the upstream status is not 200 (including 404, 409 and 422), and on any exception (`w1-gateway-api.md` F9, `w3-ddd-architecture.md` F5).
- `CHARACTER_SHEET_URL` appears in no Helm file (`w1-gates-infra.md` F7 context).
- The file is 356 lines. It mixes proxy and domain mutation code (`w1-gateway-api.md` Healthy areas, `w1-character-sheet.md` F1).
- Upstream failures return fictional character state with HTTP 200. An operator cannot see the outage.

## Documentation & Architecture Review
- Owner routes exist in `services/character_sheet/src/character_sheet/router.py`: `POST /api/v1/characters/{id}/health`, `.../equipment`, `.../equipment/{slot}`, `.../inventory`, `.../inventory/{item_id}`, `.../inventory/add`, `.../conditions`, `.../conditions/{condition}`, `.../spells/cast`, `.../spells/prepare`, `.../guardrails` (GET and PUT), and `.../penalties`.
- Verify each method and path against the owner router before coding. Record any change in the PR.
- The gateway also exposes `DELETE .../equipment/{slot}`, `DELETE .../inventory/{item_id}` and `DELETE .../conditions/{condition}`. The owner exposes the same operations as `POST .../remove` or `.../inventory/{item_id}` (DELETE). Confirm which form the owner uses and map to it.
- `wardrobe` and `portrait` are not in this task. TASK-0444 covers them.

## Product & User Story References
- [`prd-0006-digital-character-sheet-inventory-and-conditions.md`](../../product/accepted/prd-0006-digital-character-sheet-inventory-and-conditions.md)
- [`prd-0016-character-leitmotifs-and-kinetic-spell-vfx.md`](../../product/accepted/prd-0016-character-leitmotifs-and-kinetic-spell-vfx.md)
- [`us-0051-character-level-progression-and-spellbook.md`](../../user_stories/accepted/us-0051-character-level-progression-and-spellbook.md)
- [`us-0069-character-sheet-inspector-and-active-session-binding.md`](../../user_stories/accepted/us-0069-character-sheet-inspector-and-active-session-binding.md)

## Detailed Specification & Implementation Plan
1. Rewrite the subresource routes as `routers/characters_subresources_proxy.py`. Each handler forwards through `ServiceClient` (TASK-0580). Each handler is 10 lines or fewer. Pass the caller identity.
2. Pass the upstream status and body unchanged for 2xx and 4xx. Map 5xx and connection errors through the handlers from TASK-0580.
3. Delete `character_subresources.py`, `proxy_or_fallback`, and every in-memory mutation path. Delete the `CHARACTER_SHEET_URL` read.
4. Do not decompose the file into `characters/` sub-modules. Supersedes TASK-0435.
5. Update `docs/reference/ports-and-endpoints.md` for the subresource rows.

## Frontdoor Blackbox Test Plan
Test file: `tests/test_blackbox_gateway_character_subresources.py`. `character_sheet` runs as an ASGI app. Setup: create a character through the gateway.

| Case | Expected before fix | Expected after fix |
|---|---|---|
| `POST .../health` with damage, then GET shows reduced HP | Fails: in-memory update only | Passes |
| Unknown character returns the owner 404 | Fails: 200 fallback | Passes |
| Owner validation error 422 passes through | Fails: 200 fallback | Passes |
| Owner down returns 503 | Fails: 200 fallback | Passes |
| Guardrails PUT then GET returns the stored value | Fails: fallback store | Passes |

## Definition of Done
1. `character_subresources.py` is removed. `rg "proxy_or_fallback|CHARACTER_SHEET_URL" gateway/api` returns nothing.
2. Every subresource route forwards through `ServiceClient`. Each module is under 150 lines.
3. TASK-0435 is closed as superseded in the index.
4. The blackbox test file passes. `uv run ruff check .` passes.
5. `docs/reference/ports-and-endpoints.md` matches the routes.

## Orchestrator Addenda (2026-11-17, round 2)

Source: `.audit/synth/discovered-round2.md`.

- gateway/api/src/gateway_api/character_store_mutations.py: delete the functions with no callers (modify_health, equip_item, unequip_item, add_inventory_item, remove_inventory_item, apply_condition, remove_condition, cast_spell, prepare_spell, update_guardrails) and remove the gateway-held stand-in flag (about lines 62 and 244).

## Audit Provenance

- Severity: high
- Source audits: `w1-gateway-api.md`, `w1-character-sheet.md`, `w3-ddd-architecture.md`

## Orchestrator Addenda (2026-11-17, refactor-r1)

- TASK-0586 and TASK-0435 (gateway character subresources): append "`character_subresources.py:25-39` (`_forward`) is a pure pass-through of `forward_json` with a fixed service. Drop it when the module is rewritten. Same for `sessions_proxy.py` `SERVICE`." (The shared forwarder factory is not filed as a task, see deferred.)
