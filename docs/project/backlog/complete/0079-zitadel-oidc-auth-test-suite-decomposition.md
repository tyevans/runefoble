---
id: 0079
title: Zitadel OIDC Token Verification and JWKS Blackbox Test Suite Modular Decomposition
status: Complete
created: 2026-09-26
dependencies:
- TASK-0034
governing_adrs:
- ADR-0001
- ADR-0005
- ADR-0007
- ADR-0009
target_release: 0.2.0
pr_url: https://github.com/tyevans/runefoble/pull/77
---
# TASK-0079: Zitadel OIDC Token Verification and JWKS Blackbox Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_blackbox_zitadel_auth.py` (385 lines, 77.0% of limit) into two specialized test modules (`tests/test_blackbox_zitadel_http_auth.py` and `tests/test_blackbox_zitadel_websocket_auth.py`) to prevent breaching Hard Invariant 6 (File length limit < 500 lines) as new token claims and session authentication protocols are added.

## Problem Statement
`tests/test_blackbox_zitadel_auth.py` currently spans 385 lines and covers two distinct authentication surfaces introduced in TASK-0034:
1. HTTP Bearer token authentication: RSA key generation, JWKS key rotation, token expiration, signature tampering, issuer verification, and role extraction (`BearerAuthDependency`).
2. WebSocket connection authentication: Query parameter token decoding (`?token=...`), WebSocket Subprotocol token passing (`Sec-WebSocket-Protocol`), and connection rejection with RFC 6455 policy violation close frames (code 4003).

As upcoming voice streaming features and spectator interactivity expand authentication requirements across WebSockets and WebRTC signaling, this test suite will rapidly breach the 500-line ceiling unless modularized.

## Governing Architecture & ADRs
- **ADR-0001**: SpiceDB Zanzibar Object Authorization.
- **ADR-0005**: Kubernetes-First Infrastructure with Helm and Kind (Zitadel OIDC provider).
- **ADR-0007**: Real-Time Voice and Board Synchronization (WebSocket auth).
- **ADR-0009**: Continuous Backlog Refinement and Technical Debt Management.

## Proposed Decomposition
1. **HTTP Bearer & JWKS Blackbox Suite (`tests/test_blackbox_zitadel_http_auth.py`)**:
   - RSA test keypair generation and JWK formatting fixtures.
   - HTTP Bearer token verification, audience/issuer validation, signature tamper checks, and expired token rejections (< 210 lines).
2. **WebSocket Zitadel Token Auth Suite (`tests/test_blackbox_zitadel_websocket_auth.py`)**:
   - WebSocket query parameter authentication (`/ws/campaigns/{id}?token=...`).
   - WebSocket Subprotocol header authentication.
   - Invalid token close codes (4003) and anonymous user reject policies (< 190 lines).
3. **Original Monolith Deletion**:
   - Remove `tests/test_blackbox_zitadel_auth.py`.

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors test organization without modifying gateway auth middleware, Zitadel service logic, or FastAPI endpoints.
- **Negotiable (N)**: Helper fixture sharing can be adapted between modules or placed in a shared auth fixture module.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (< 500 lines) and enables fast, targeted test execution for HTTP vs WebSocket auth.
- **Estimable (E)**: Clean separation of HTTP Bearer tests from WebSocket handshake tests.
- **Small (S)**: Scope strictly isolated to `tests/test_blackbox_zitadel_auth.py`; all resulting files < 220 lines.
- **Testable (T)**: Verified with `uv run pytest tests/test_blackbox_zitadel_*.py`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Modular Test Suite Partitioning**:
   - `tests/test_blackbox_zitadel_auth.py` decomposed into `tests/test_blackbox_zitadel_http_auth.py` and `tests/test_blackbox_zitadel_websocket_auth.py`.
2. **Strict File Length Compliance (Hard Invariant 6)**:
   - All resulting test files strictly under 220 lines each.
3. **Frontdoor Blackbox Verification**:
   - 100% test pass rate across all existing HTTP Bearer and WebSocket authentication tests.
4. **Original Monolith Removal**:
   - `tests/test_blackbox_zitadel_auth.py` deleted.
5. **Quality Gates**:
   - Passes `uv run ruff check` and `uv run ruff format --check`.
