---
id: '0594'
title: Gateway Rules Compendium Proxy for Rules, Encounters, and Homebrew
status: Complete
created: 2026-11-17
dependencies:
- TASK-0580
- TASK-0625
governing_adrs:
- ADR-0001
- ADR-0007
governing_prds:
- PRD-0008
governing_stories:
- US-0037
- US-0052
target_release: 0.9.0
---

# TASK-0594: Gateway Rules Compendium Proxy for Rules, Encounters, and Homebrew

## Status
Complete

## Summary
`rules_compendium` is not reachable through the gateway. `gateway/api/src` has no compendium route. The how-to tells browsers to call `localhost:8007` directly. Add gateway proxies for the public compendium routes. Forward the caller identity. Update the how-to so the UI calls the gateway.

## Problem Statement
- `gateway/api/src` has no route, proxy or string for `compendium` or port `8007` (`w2-rules-compendium.md` F6).
- `deployments/helm/runefoble/values.yaml:15-18` sends only `/api` to the gateway. A browser request to `/api/v1/compendium/*` reaches a gateway that does not serve it.
- `docs/how-to/balance-combat-encounters-and-query-compendium.md:209,217` sets `apiBaseUrl="http://localhost:8007"` for the UI.
- The compendium's SpiceDB token is a literal (`w2-rules-compendium.md` F3). TASK-0625 fixes it. This task depends on that fix so the proxied service works in the cluster.

## Documentation & Architecture Review
- The owner routes (in `services/rules_compendium/src/rules_compendium/routers/`):
  - `rules.py` (prefix `/api/v1/compendium`): `GET /rules/search`, `GET /monsters/{name}`, `GET /spells/{name}`, `GET /conditions/{name}`.
  - `encounters.py` (prefix `/api/v1/compendium/encounters`): `POST /balance` and the builder routes.
  - `homebrew.py` (prefix `/api/v1/compendium/homebrew`): `POST` and `GET /{campaign_id}`.
- `gateway_mcp` imports compendium internals directly (`w1-gateway-mcp.md` F6). That fix belongs to the MCP theme. This task does not change `gateway_mcp`.
- Homebrew rules are campaign-scoped (`w2-rules-compendium.md` F4). The owner decides the scope. This task does not change it.

## Product & User Story References
- [`prd-0008-ttrpg-rules-compendium-and-encounter-builder.md`](../../product/accepted/prd-0008-ttrpg-rules-compendium-and-encounter-builder.md)
- [`us-0037-automated-cr-encounter-balancing-and-compendium.md`](../../user_stories/accepted/us-0037-automated-cr-encounter-balancing-and-compendium.md)
- [`us-0052-homebrew-spell-monster-and-rule-authoring.md`](../../user_stories/accepted/us-0052-homebrew-spell-monster-and-rule-authoring.md)

## Detailed Specification & Implementation Plan
1. Create `gateway/api/src/gateway_api/routers/compendium_proxy.py`. Forward each owner route through `ServiceClient` (TASK-0580). Map the path and query string unchanged. Pass the caller identity.
2. Add the `RULES_COMPENDIUM` setting from TASK-0580 and the Helm variable from TASK-0624.
3. Update `docs/how-to/balance-combat-encounters-and-query-compendium.md` so the base URL is the gateway. Remove the `localhost:8007` example.
4. Update `docs/reference/ports-and-endpoints.md` with the gateway rows.
5. Do not change the SpiceDB check in the owner in this task. The authorization theme owns it.

## Frontdoor Blackbox Test Plan
Test file: `tests/test_blackbox_gateway_compendium_proxy.py`. `rules_compendium` runs as an ASGI app.

| Case | Expected before fix | Expected after fix |
|---|---|---|
| `GET /api/v1/compendium/monsters/{name}` through the gateway returns the owner's stat block | Fails: 404 | Passes |
| `POST /api/v1/compendium/encounters/balance` returns the owner's CR result | Fails: 404 | Passes |
| Homebrew written through the gateway is read back through the gateway | Fails: 404 | Passes |
| Owner down returns 503 | Fails: 404 | Passes |

## Definition of Done
1. Every owner route in the list is reachable through the gateway.
2. `rg "8007" docs/how-to gateway/api/src` returns no compendium base URL.
3. The blackbox test file passes. `uv run ruff check .` passes.
4. The how-to and the ports reference match the routes.

## Audit Provenance

- Severity: high
- Source audits: `w2-rules-compendium.md`, `w3-ddd-architecture.md`, `w1-gateway-mcp.md`
