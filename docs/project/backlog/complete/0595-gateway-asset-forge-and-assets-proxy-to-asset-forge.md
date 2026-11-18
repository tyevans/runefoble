---
id: '0595'
title: Gateway Asset Forge and Assets Proxy to Asset Forge
status: Complete
created: 2026-11-17
dependencies:
- TASK-0580
governing_adrs:
- ADR-0005
- ADR-0007
governing_prds:
- PRD-0009
- PRD-0015
governing_stories:
- US-0038
- US-0049
target_release: 0.9.0
---

# TASK-0595: Gateway Asset Forge and Assets Proxy to Asset Forge

## Status
Complete

## Summary
`asset_forge` has no gateway route. The forge routes exist only on port 8008, and the ingress does not reach them. The gateway also serves `/api/v1/assets` in process from a platform storage library. Replace that router with proxies to `asset_forge`. Add gateway proxies for the battlemap, token, print, standee and STL routes.

## Problem Statement
- `deployments/helm/runefoble/values.yaml` ingress sends only `/api` to the gateway. The forge routes are reachable only on 8008 (`w2-asset-forge.md` F3).
- No route exists for `/api/v1/forge/battlemap`, `/api/v1/forge/token`, `/api/v1/forge/wardrobe`, `/api/v1/forge/print-pdf`, `/api/v1/forge/standees` or `/api/v1/forge/stl-token` in `gateway/api/src` (`w2-asset-forge.md` F3).
- `gateway/api/src/gateway_api/assets.py` (removed), which ran in process, uploads and deletes assets with no auth. Its `_resolve_user_id` uses the raw bearer token (`w1-gateway-api.md` F5). It publishes events twice (`w1-gateway-api.md` F21).
- `main.py:83` mounts the assets router with `prefix="/api/v1/assets"`.

## Documentation & Architecture Review
- Owner routes (`services/asset_forge/src/asset_forge/routers/`):
  - `battlemap.py` (`/api/v1/forge/battlemap`), `token.py` (`/api/v1/forge/token`), `wardrobe.py` (`/api/v1/forge/wardrobe`).
  - `print_forge.py` has both `/assets/print-pdf` and `/api/v1/forge/print-pdf` forms. Use the `/api/v1/forge/` form only (DoR 9, no aliases). Check that the other form has no caller.
- Character wardrobe (`/api/v1/characters/{id}/wardrobe`) is owned by `character_sheet`, not `asset_forge`. TASK-0444 covers it. This task does not touch it.
- `asset_forge` stores bytes through Silo (`w2-asset-forge.md` F1). The owner must fail on a Silo error. That fix belongs to the owner, not to this task.
- ADR-0005: the forge image is deployed through Helm. Confirm the Helm service for `asset_forge` exists before the proxy goes live.

## Product & User Story References
- [`prd-0009-procedural-battlemap-and-token-asset-generation.md`](../../product/accepted/prd-0009-procedural-battlemap-and-token-asset-generation.md)
- [`prd-0015-generative-handouts-relic-inspector-and-printable-forge.md`](../../product/accepted/prd-0015-generative-handouts-relic-inspector-and-printable-forge.md)
- [`us-0038-generative-procedural-battlemaps-and-tokens.md`](../../user_stories/accepted/us-0038-generative-procedural-battlemaps-and-tokens.md)
- [`us-0049-printable-tabletop-forge-and-stl-tokens.md`](../../user_stories/accepted/us-0049-printable-tabletop-forge-and-stl-tokens.md)

## Detailed Specification & Implementation Plan
1. Create `gateway/api/src/gateway_api/routers/forge_proxy.py`. Forward the battlemap, token, wardrobe, print-pdf, standees and stl-token routes through `ServiceClient` (TASK-0580). Map the binary response unchanged (content type and body bytes).
2. Replace `assets.py` with `assets_proxy.py`. Forward upload, read and delete to the `asset_forge` owner routes. Verify the owner has them. If the owner does not, add them to `asset_forge` in this change. Use the verified principal, never the raw token.
3. Delete `assets.py`, the in-process asset storage calls and the double event publish. Remove the `main.py` mount at line 83.
4. Add the `ASSET_FORGE` setting (TASK-0580) and Helm variable (TASK-0624).
5. Update `docs/reference/ports-and-endpoints.md` and any forge how-to that names port 8008 as a browser endpoint.
6. Record in the index that TASK-0348 (assets router decomposition) is superseded by this task.

## Frontdoor Blackbox Test Plan
Test file: `tests/test_blackbox_gateway_forge_proxy.py`. `asset_forge` runs as an ASGI app.

| Case | Expected before fix | Expected after fix |
|---|---|---|
| `POST /api/v1/forge/token` through the gateway returns the owner's PNG bytes | Fails: 404 | Passes |
| `POST /api/v1/forge/print-pdf` returns `application/pdf` from the owner | Fails: 404 | Passes |
| Asset upload then GET through the gateway returns the same bytes | Fails: 404 or in-memory | Passes |
| Delete without an identity returns 401 | Fails: 200 | Passes |
| Owner down returns 503 | Fails: 404 | Passes |

## Definition of Done
1. `assets.py` is removed. `rg "_resolve_user_id|authorization\[7:\]" gateway/api/src` returns nothing.
2. Every forge route in the list is reachable through the gateway.
3. The blackbox test file passes. `uv run ruff check .` passes.
4. The ports reference names the gateway as the browser endpoint for forge routes.

## Audit Provenance

- Severity: high
- Source audits: `w2-asset-forge.md`, `w1-gateway-api.md`, `w3-ddd-architecture.md`
