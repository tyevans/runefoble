---
id: '0521'
title: Gateway HTTP Routes Authenticate Through the Verified Principal
status: Complete
created: 2026-11-17
dependencies:
- TASK-0520
governing_adrs:
- ADR-0001
- ADR-0005
- ADR-0013
governing_prds:
- PRD-0023
governing_stories:
- US-0013
- US-0062
target_release: 0.9.0
---

# TASK-0521: Gateway HTTP Routes Authenticate Through the Verified Principal

## Status
Complete

## Summary
Make the gateway HTTP layer accept identity only from a verified Zitadel bearer token. Remove the dev identity path, the `X-User-Id` header as identity, the `guest_user` fallback, the raw-bearer user id, and the hardcoded `the_watcher_dm` default. Restrict CORS to an explicit origin list.

## Problem Statement
- `gateway/api/src/gateway_api/auth.py:95-104` (`get_current_user`) returns a dev admin with roles `player,dm` when no bearer is sent. It takes `X-User-Id` as the subject. Audit w1-gateway-api F3.
- `auth.py:140-152` (`require_zanzibar_permission._checker`) does the same and falls back to `guest_user`.
- `services/asset_forge/src/asset_forge/routers/assets.py:85` (`POST /upload`) has no auth dependency. `assets.py:237` (`DELETE /{asset_id}`) takes the owner from `_resolve_user_id` (lines 78-84), which returns the raw bearer text. Audit w1-gateway-api F5.
- `gateway/api/src/gateway_api/companion/router.py` (removed) takes `x_user_id` with default `"the_watcher_dm"`. Audit w1-gateway-api F22.
- `gateway/api/src/gateway_api/main.py:55-70` sets `allow_origins` to include `"*"` and `allow_credentials=True`. Audit w3-authz F19.
- Audit w3-authz route table rows 1-2, 9-52, and others: every route that uses the dev path or the header identity.

## Documentation & Architecture Review
- TASK-0520 provides `require_principal` and `VerifiedPrincipal`. Use them. Do not add a second verifier.
- `docs/reference/ports-and-endpoints.md` lists gateway routes. Update any identity wording there (TASK-0537 consolidates).
- Route-level SpiceDB checks (`require_zanzibar_permission` permission names) belong to the authorization theme. This task changes only where the subject comes from.

## Product & User Story References
- US-0013: gateway authorization must use a verified subject before any Zanzibar check.
- US-0062: sign-in must produce a real identity that the gateway verifies.

## Detailed Specification & Implementation Plan
1. **`auth.py`**
   - `get_current_user` becomes a thin alias of `require_principal` from TASK-0520. Delete the dev branch, the `x_user_id` parameter, and the admin role.
   - `require_zanzibar_permission` depends on `principal: VerifiedPrincipal = Depends(require_principal)`. The subject is `principal.user_id`. Delete `guest_user`.
   - Keep the public route list explicit: `/health`, `/openapi.json`, `/docs`, and `/ui/manifest`. Every other route requires a verified principal.
2. **All gateway routes**
   - No handler reads `X-User-Id` or the raw `Authorization` value. Verify with `grep -rn "X-User-Id\|x-user-id\|guest_user\|the_watcher_dm" gateway/api/src`.
   - Routes that already use `require_zanzibar_permission` inherit the verified subject. Routes that take no identity (for example `POST /api/v1/campaigns/join`) add `Depends(require_principal)`.
3. **Assets (`assets.py`)**
   - Upload and delete depend on `require_principal`. Owner is `principal.user_id`. Delete `_resolve_user_id`.
   - The SpiceDB ownership check on delete belongs to the authorization theme. Note it in the PR.
4. **Companion (`companion/router.py`)**
   - Remove the header parameter and its default. Use the principal.
5. **Profile (`routers/auth/profile.py`)**
   - Use the principal for `GET` and `PATCH`. The in-memory profile store is a separate defect and is out of scope here.
6. **CORS (`main.py`)**
   - Read `RUNEFOBLE_CORS_ORIGINS` (comma-separated). No `"*"` when credentials are allowed. Default: the local App Shell origin only.
7. **Remove `is_admin` branches** in gateway modules. Use `grep -rn is_admin gateway/api/src`.

## Frontdoor Blackbox Test Plan
New file `tests/test_blackbox_gateway_identity_http.py`, using `TestClient(app)` and tokens from the signing issuer.
- Before: `GET /api/v1/profile` with `Authorization: Bearer not-a-real-jwt` returns 200 with `is_admin: true`. `POST /api/v1/assets/upload` with no identity returns 200.
- After:
  - No bearer and garbage bearer return 401 on `GET /api/v1/profile`, `POST /api/v1/campaigns`, and `POST /api/v1/assets/upload`.
  - A valid token with `X-User-Id: someone-else` returns a profile whose `user_id` equals the token `sub`.
  - Asset upload stores the token `sub` as owner. A second user's delete through `DELETE /api/v1/assets/{id}` is not accepted by identity alone (authorization theme enforces ownership).
  - An `Origin` not in the allow list gets no `Access-Control-Allow-Origin` header.

## Definition of Done
1. Gateway HTTP routes have no identity path except `require_principal`. The grep in step 2 returns no matches in `gateway/api/src`.
2. `uv run pytest tests/test_blackbox_gateway_identity_http.py` passes. Existing gateway suites are updated to use the signing issuer and pass.
3. Integrated in one merge with TASK-0520.
4. `uv run ruff check gateway/api` passes. No file exceeds 500 lines.
5. `CHANGELOG.md` `[Unreleased]` notes that gateway routes require a bearer token.

## Audit Provenance

- Severity: critical
- Source audits: `w1-gateway-api.md`, `w3-authz-coverage.md`, `w3-ddd-architecture.md`
