---
id: '0527'
title: Services Verify Zitadel Tokens (board_state, campaign_analytics, rules_compendium)
status: Complete
created: 2026-11-17
dependencies:
- TASK-0520
- TASK-0536
governing_adrs:
- ADR-0001
- ADR-0005
- ADR-0007
governing_prds:
- PRD-0003
- PRD-0008
- PRD-0012
governing_stories:
- US-0013
target_release: 0.9.0
severity: critical
source_audits:
- w1-board-state.md
- w2-campaign-analytics.md
- w2-rules-compendium.md
- w3-authz-coverage.md
---

# TASK-0527: Services Verify Zitadel Tokens (board_state, campaign_analytics, rules_compendium)

## Status
Complete

## Summary
Three bounded contexts take caller identity from a plain `x-user-id` header. Any client that reaches the service can claim any user. Replace the header identity with the verified principal from TASK-0520 in each service, applied to every router. Remove the `None` branches that let an anonymous caller pass.

## Problem Statement
- `services/board_state/src/board_state/dependencies.py:66-71` (`get_current_user_id`) returns the raw `x-user-id` header. Audit w1-board-state F15.
- `services/campaign_analytics/src/campaign_analytics/dependencies.py:82` returns `True` when no `X-User-ID` header exists ("Public viewing permitted"). Audit w2-campaign-analytics F7.
- `services/rules_compendium/src/rules_compendium/dependencies.py:62-65` returns the header. `check_user_can_view_campaign` returns `True` when `user_id` is empty (line 75). Audit w2-rules-compendium F1, F2. Probe: `POST /api/v1/compendium/homebrew` with `x-user-id: dm1` and no credential returns 200.
- Audit w3-authz F9: all services take identity from the header.
- `board_state` also seeds fake PCs when an unknown id is read (`w1-board-state` F5). That is a fake-implementation defect and is out of scope here.

## Documentation & Architecture Review
- The service verifies the token itself. The gateway forwards the `Authorization` header (TASK-0536). A trusted gateway header is rejected as a trust boundary: see the index report.
- Service-side SpiceDB checks and relation names belong to the authorization theme.
- The literal SpiceDB key in these services is handled by TASK-0625.
- `docs/how-to/manage-secret-dm-traps-and-map-triggers.md` uses `x-user-id` in examples. Update it.

## Product & User Story References
- US-0013 (authorization requires a verified subject). PRD-0003 (board visibility), PRD-0008 (rules compendium), PRD-0012 (telemetry).

## Detailed Specification & Implementation Plan
1. In each service, add the platform settings for issuer, audience, and JWKS URL. Read them from `PlatformSettings`.
2. Replace `get_current_user_id` with a dependency built on `require_principal` from `runefoble_auth`. Return `principal.user_id`.
3. Apply the identity dependency at the router level (`APIRouter(dependencies=[...])`), so every route in the router has a non-null `user_id`.
4. Delete every route that reads `x-user-id` or `X-User-ID` directly. Use `grep -rn -i "x-user-id" services/board_state services/campaign_analytics services/rules_compendium/src`.
5. Change helper signatures so `user_id` is `str`. Delete the early `return True` and `if not user_id` branches in these three services. The authorization theme owns the deny logic that replaces them.
6. Keep `/health`, `/openapi.json`, and `/ui/manifest` public.
7. Helm: add the three issuer variables to the service templates (`deployments/helm/runefoble/templates/services.yaml`). TASK-0624 also edits this file. Coordinate.

## Frontdoor Blackbox Test Plan
HTTP tests with `TestClient`, using tokens from the signing issuer. New file per service under the service's `tests/` or the root `tests/` directory.
- Before: anonymous `POST /api/v1/compendium/homebrew` with `x-user-id: dm1` returns 200. Anonymous `GET` of campaign analytics returns 200.
- After:
  - No bearer, garbage bearer, and forged token return 401 on every mutating and read route in the three services.
  - Valid bearer for `dm1` with `x-user-id: dm2` writes the rule as `dm1`.
  - `/health` and `/openapi.json` stay 200 without a bearer.

## Definition of Done
1. `grep -rn -i "x-user-id" services/board_state services/campaign_analytics services/rules_compendium --include=*.py` returns only test fixtures or nothing.
2. Service test suites pass with the signing issuer.
3. Helm renders the new variables (`helm template`).
4. `docs/how-to/manage-secret-dm-traps-and-map-triggers.md` and the three service how-tos show a bearer token.
5. `uv run ruff check services/board_state services/campaign_analytics services/rules_compendium` passes. No file exceeds 500 lines.
