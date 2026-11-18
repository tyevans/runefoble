---
id: '0520'
title: Verified Principal Library, Dev Identity Removal, and JWT Hardening
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0001
- ADR-0005
- ADR-0007
governing_prds:
- PRD-0023
governing_stories:
- US-0062
- US-0013
target_release: 0.9.0
---

# TASK-0520: Verified Principal Library, Dev Identity Removal, and JWT Hardening

## Status
Complete

## Summary
Make `libs/runefoble_auth` the only identity verifier in the platform. Remove the dev mode, the dev user fallback, the non-verifying decode path, and admin derivation from role names. Add one verified-principal model, a FastAPI dependency, a WebSocket handshake helper, and a signing test issuer. Every later identity task depends on this library.

## Problem Statement
- `libs/runefoble_auth/src/runefoble_auth/zitadel.py:51-53` sets `RUNEFOBLE_AUTH_DEV_MODE` to `"true"` by default. Audit w1-libs F1.
- `zitadel.py:96-117` (`_dev_mock_decode`) skips signature and expiry checks. Any decode error returns `dev-user-001` with `is_admin=True`.
- `libs/runefoble_platform/src/runefoble_platform/config.py:83-86` sets `auth_dev_mode` to `True` by default.
- `zitadel.py:36,38` leave `verify_audience` and `verify_issuer` off by default. Any token signed by the same Zitadel instance is accepted. Audit w1-libs F4.
- `zitadel.py:166-171` (`decode_token`, `verify=False` by default) is a backward-compatibility shim. Audit w1-libs F9, w3-authz F18.
- `zitadel.py:93` derives `is_admin` from the string `"admin"` in roles. This breaks Hard Invariant 1. Audit w1-libs F3.
- Audit probe (w3-authz F1): `Authorization: Bearer not-a-real-jwt` on `GET /api/v1/profile` returns `is_admin: true`.
- Audit probe (w3-ddd F1): an unsigned token with `sub=user-dm-evelyn` authenticates as that user.
- No unit tests cover JWT verification. Audit w1-libs F15.

## Documentation & Architecture Review
- `AGENTS.md` Hard Invariant 1 (no role checks in business logic) and invariant 7 (frontdoor tests only).
- `AGENTS.md` DoR 9 (no backward-compatibility shims). Delete `decode_token` and `AuthenticatedUser`. Update every call site in the same change.
- `docs/how-to/authenticate-with-zitadel-oidc.md` lines 58 and 94 describe dev mode and the `dev-user-001` bypass. Rewrite these sections in this task. Audit w1-libs F17, w3-docs-integrity PS2.
- `docs/project/adrs/accepted/adr-0005-kubernetes-first-infrastructure-with-helm-and-kind.md` names Zitadel as the identity container.
- TASK-0034 (complete) added JWKS verification but kept the dev bypass. TASK-0486 (refined) names classes that do not exist (`ZitadelAuthClient`, `verify_token_async`, `UserTokenClaims`). Its shim items overlap this task. See the index report for the correction.
- Generic reusable pattern: this task creates the verified-principal dependency used by all services. Author a Diataxis how-to at `docs/how-to/verify-identity-in-fastapi-and-websockets.md`.

## Product & User Story References
- PRD-0023 requires Zitadel OIDC with PKCE and no bypass. See `docs/project/product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md`.
- US-0062 (Zitadel sign-in) and US-0013 (gateway authorization) are the governing stories.

## Detailed Specification & Implementation Plan
1. **Verifier (`zitadel.py`)**
   - Delete the `dev_mode` parameter, the `RUNEFOBLE_AUTH_DEV_MODE` read, `_dev_mock_decode`, `decode_token`, and the `verify` override.
   - `verify_token(token, audience=None)` always verifies the signature. It accepts only `RS256`. It always checks `exp`, `sub`, `iss`, and `aud`.
   - Constructor: `issuer` (expected `iss`), `audience` (expected `aud`), `jwks_url`, `jwk_client` (test injection). Remove `verify_audience` and `verify_issuer`.
   - Default `jwks_url` comes from OIDC discovery (`jwks_uri`). Do not assume `/.well-known/jwks.json`. Zitadel exposes its keys at a different path.
   - Remove the `is_admin` field and the `"admin"` role check.
2. **Principal model and FastAPI dependency (`principal.py`, new)**
   - `VerifiedPrincipal(user_id: str, username: str, email: str | None)`. It has no roles and no admin flag. Roles are not authority.
   - `require_principal(request, authorization=Header(...))` reads only `Authorization: Bearer`. It returns the principal or raises HTTP 401 with `WWW-Authenticate: Bearer`. It has no fallback.
   - Replace `AuthenticatedUser` with `VerifiedPrincipal`. Update all importers in `libs/`, and the gateway import in `gateway/api/src/gateway_api/auth.py`, in the same change.
3. **WebSocket helper (`websocket.py`, new)**
   - Browsers cannot set `Authorization` on a WebSocket. The client offers the subprotocols `runefoble.v1` and `runefoble.bearer.<jwt>`.
   - `authenticate_websocket(websocket) -> VerifiedPrincipal` reads the offered protocols and verifies the token. On failure it raises `WebSocketAuthError`.
   - The caller rejects the handshake before accept. On success the caller accepts with `subprotocol="runefoble.v1"`.
   - Do not accept a token in the URL query string.
4. **Test issuer (`runefoble_auth/testing/signing_test_issuer.py`, new)**
   - Generates an RSA key pair, mints RS256 tokens with chosen `sub`, `aud`, `iss`, and `exp`, and produces a JWK set plus a `jwk_client` stub.
   - All test suites use this issuer. Remove `tests/helpers/zitadel_auth.py` dev-mode helpers when callers move (see TASK-0535).
5. **Settings (`config.py`)**
   - Delete `auth_dev_mode` and every `AUTH_DEV_MODE` alias.
   - Keep `zitadel_issuer` (the external URL that Zitadel writes into `iss`). Keep `zitadel_jwks_url` (internal URL for key fetch). Add `zitadel_audience` (default `zitadel_client_id`).
6. **Callers in the library**: `sync.py` and `sync_tuples.py` use `verify_token` and `VerifiedPrincipal`. Their claim policy changes in TASK-0534.
7. **Docs**: rewrite the dev-mode sections in `docs/how-to/authenticate-with-zitadel-oidc.md`. Add the new how-to named above.

## Frontdoor Blackbox Test Plan
Library tests use the public dependency through a minimal FastAPI app and `TestClient`.
- Before: `ZitadelAuthService()` with default settings accepts a forged HS256 token and an unsigned token.
- After, in `libs/runefoble_auth/tests/test_verified_principal.py`:
  - A valid RS256 token from the signing issuer is accepted.
  - Each of these is rejected with 401: no header, garbage string, HS256 signed with a known secret, `alg: none`, unsigned, RS256 from an unknown key, expired, wrong `aud`, wrong `iss`, missing `sub`.
  - Setting `RUNEFOBLE_AUTH_DEV_MODE=true` does not change any result.
  - WebSocket: missing protocol and forged protocol are denied before accept. A valid protocol is accepted and echoes `runefoble.v1`.
- Integrate with TASK-0521 in one merge. The gateway is the only in-repo consumer that depends on the dev path.

## Definition of Done
1. No dev mode, dev user, `decode_token`, `is_admin`, or `AuthenticatedUser` remains in `libs/` or `gateway/`. Verify with `grep -rn "dev_mode\|dev-user-001\|decode_token\|is_admin\|AuthenticatedUser" libs gateway`.
2. `uv run pytest libs -q` passes, including the new test file.
3. The how-to `verify-identity-in-fastapi-and-websockets.md` exists. The authenticate how-to no longer describes dev mode.
4. `uv run ruff check libs` passes. No file exceeds 500 lines.
5. `CHANGELOG.md` `[Unreleased]` records the removed dev mode and the new principal contract.

## Audit Provenance

- Severity: critical
- Source audits: `w1-libs.md`, `w3-authz-coverage.md`, `w3-ddd-architecture.md`, `w3-docs-integrity.md`, `w1-gateway-api.md`
