---
id: '0556'
title: Asset Forge Creator Identity and Campaign Authorization
status: Refined
created: 2026-11-17
dependencies:
- TASK-0520
- TASK-0541
- TASK-0542
- TASK-0540
- TASK-0528
governing_adrs:
- ADR-0001
- ADR-0007
- ADR-0014
governing_prds:
- PRD-0009
- PRD-0015
governing_stories:
- US-0038
- US-0049
- US-0055
target_release: 0.9.0
---

# TASK-0556: Asset Forge Creator Identity and Campaign Authorization

## Status
Refined

## Summary
The asset forge checks campaign permission only when a campaign is given, and it takes identity from an unchecked header. Creator relations are written inside `contextlib.suppress`, so a failed grant still returns success, and the creator id falls back to `anonymous_creator`. This task applies the forge permission to every forge route, uses the verified principal for the creator, and stops silent grant failures.

## Problem Statement
- `services/asset_forge/src/asset_forge/dependencies.py` `get_current_user_id` returns the raw `x-user-id` header. `check_user_can_forge` returns True when no campaign is given (`w2-asset-forge.md` F4).
- Forge routes that call `check_user_can_forge` and pass for anonymous callers (`w3-authz-coverage.md` rows 73-82): `routers/battlemap.py:35`, `routers/print_forge.py:56,152,220` (plus the `/api/v1/forge/*` aliases), `routers/token.py:34`, `routers/wardrobe.py:29` (plus `/generate`).
- `routers/battlemap.py`, `token.py`, `wardrobe.py`, `print_forge.py`: the `forged_asset` `creator` and `campaign` writes sit inside `with contextlib.suppress(Exception):`. A failed write leaves the asset with no creator, so `forged_asset.manage` is never granted (`w2-asset-forge.md` F4).
- The client falls back to `anonymous_creator` and `anonymous_crafter` (`w2-asset-forge.md` F4).
- `services/asset_forge/src/asset_forge/dependencies.py:76` reads `spicedb_token` (`w3-ddd-architecture.md` F9). TASK-0625 fixes the setting. TASK-0541 replaces the factory.

## Documentation & Architecture Review
- ADR-0001: `forged_asset.view` for reads (campaign view or creator). `forged_asset.manage` for edits and deletes (creator or campaign manage). Forge actions require `campaign.play`.
- ADR-0007: the asset context owns forged assets. Silo storage is owned by the storage task (`w2-asset-forge.md` F1 is a fake-implementation issue, not this task).
- `docs/how-to/forge-procedural-battlemaps-and-tokens.md`, `docs/how-to/manage-generative-wardrobe-and-condition-portraits.md`, and `docs/how-to/forge-print-ready-maps-standees-and-stl-tokens.md` describe these routes. Update the auth text.
- Routes are mounted with both `/assets/...` and `/api/v1/forge/...` prefixes (`w3-authz-coverage.md` rows 73-82). Keep one prefix per route in this task. Remove the duplicate mounts in the same change.

## Product & User Story References
- US-0038 (procedural battlemaps and tokens). US-0049 (printable forge and STL tokens). US-0055 (wardrobe and condition portraits). PRD-0009 and PRD-0015.

## Detailed Specification & Implementation Plan
1. `dependencies.py` (the principal comes from TASK-0528):
   - The creator is the principal from TASK-0528.
   - `check_user_can_forge` requires a campaign. A request with no campaign returns 400. Remove the True branch.
   - Forge actions check `campaign.play`. Asset reads check `forged_asset.view`.
   - Delete the local `get_spicedb_client` and import the library factory.
2. Each forge route writes the asset's `creator` and `campaign` relations in the same operation as the asset save. The write is not suppressed. A failed write returns 503 and the asset is not returned.
3. Remove `anonymous_creator` and `anonymous_crafter` defaults in the service and the client code paths that send them.
4. Remove the duplicate route mounts. Keep `/api/v1/forge/...` as the public prefix. Update the gateway routing reference in `docs/reference/ports-and-endpoints.md`.

## Frontdoor Blackbox Test Plan
Setup: a campaign with a player, a spectator, and the DM. Assets are created through the forge routes.
- Before the fix, anonymous `POST /api/v1/forge/battlemap` returns 200. After the fix it returns 401.
- A spectator `POST /api/v1/forge/token` returns 403. A player returns 200.
- A forge request with no campaign id returns 400. Before the fix it returns 200.
- Setup for the creator relation: the creator forges an asset (200). A different player calls `DELETE` on it (if the delete route exists) and gets 403. The creator gets 200.
- A stubbed SpiceDB write failure returns 503 and no asset is listed.

## Definition of Done
1. Frontdoor tests exist in `tests/test_blackbox_asset_forge_authz.py` and pass against the live harness.
2. `grep -rn "anonymous_creator\|anonymous_crafter\|contextlib.suppress" services/asset_forge/src` returns nothing for permission writes.
3. Each forge route is mounted once under `/api/v1/forge`.
4. The three how-to docs above are updated.
5. `uv run pytest services/asset_forge` passes. `uv run ruff check services/asset_forge` passes.
6. No file in the change exceeds 500 lines.

## Audit Provenance

- Severity: high
- Source audits: `w2-asset-forge.md`, `w3-authz-coverage.md`
