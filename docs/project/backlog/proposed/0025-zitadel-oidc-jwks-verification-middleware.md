---
id: 0025
title: Zitadel Production OIDC/JWKS Token Verification Middleware
status: Proposed
created: 2026-09-25
dependencies: [TASK-0008, TASK-0016]
governing_adrs: [ADR-0001, ADR-0005, ADR-0007]
target_release: 0.1.0
---

# TASK-0025 — Zitadel Production OIDC/JWKS Token Verification Middleware

## Summary
Upgrade `ZitadelAuthService` in `libs/runefoble_auth` from an offline stub into a production OIDC JWT verification client. Fetch and cache JSON Web Key Sets (JWKS) from Zitadel's discovery endpoint (`/.well-known/jwks.json`), cryptographically verify RS256 token signatures, validate expiration and audience claims, and inject the authenticated subject into Gateway HTTP endpoints and WebSocket handshakes.

## INVEST Criteria Evaluation
- **Independent (I)**: Operates at the gateway ingress/authentication boundary. Upgrades the authentication layer without altering SpiceDB Zanzibar authorization schema or downstream domain aggregates.
- **Negotiable (N)**: JWKS cache TTL, offline dev bypass mode (flagged via `RUNEFOBLE_AUTH_DEV_MODE`), and token audience validation parameters can be adjusted per environment.
- **Valuable (V)**: Protects game sessions and character sheet state against spoofed `X-User-Id` headers and unverified Bearer tokens; ensures tamper-proof player identity across the platform.
- **Estimable (E)**: Standard PyJWT with cryptography JWKS client (`jwt.PyJWKClient`); well-established OIDC validation patterns; governed by ADR-0005.
- **Small (S)**: Scope focused on `libs/runefoble_auth/src/runefoble_auth/zitadel.py`, `gateway_api/auth.py`, and `gateway_api/websocket.py`. Each file remains under 500 lines.
- **Testable (T)**: Frontdoor blackbox tests generating mock RS256 signed JWTs with local test keypairs, verifying valid tokens grant access, while expired, forged, or unauthenticated requests yield HTTP 401 Unauthorized through public gateway routes.

## Governing Architecture & ADRs
- **ADR-0001**: Zanzibar Object-Level Authorization (authenticated Zitadel `user_id` is supplied as `subject_id` into SpiceDB).
- **ADR-0005**: Kubernetes-First Infrastructure with Zitadel self-hosted identity.
- **ADR-0007**: Domain-Driven Design Architecture (authentication separated from authorization).

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **OIDC JWKS Verification Client (`libs/runefoble_auth/src/runefoble_auth/zitadel.py`)**:
   - `ZitadelAuthService.verify_token(token: str) -> AuthenticatedUser` utilizing `jwt.PyJWKClient` with configurable JWKS URL, caching, and signature verification.
   - Preserves offline/dev mock bypass when `verify=False` or `RUNEFOBLE_AUTH_DEV_MODE=true`.
2. **Gateway HTTP & WebSocket Auth Middleware Integration**:
   - Update `gateway/api/src/gateway_api/auth.py` dependency to decode Zitadel bearer token and set verified user context.
   - Update `gateway/api/src/gateway_api/websocket.py` to validate query token / Bearer token via `ZitadelAuthService` before accepting or authorizing connection.
3. **Blackbox TDD Suite (`tests/test_blackbox_zitadel_auth.py`)**:
   - Tests public `/api/v1/...` and `/ws/campaigns/...` routes using RSA keypair:
     - Valid signed token succeeds and extracts subject.
     - Forged/tampered signature rejected with 401 Unauthorized.
     - Expired token rejected with 401 Unauthorized.
4. **Diataxis Documentation**:
   - Create `docs/how-to/authenticate-with-zitadel-oidc.md`.
5. **File Invariant Check**:
   - All modified files remain strictly under 500 lines.
