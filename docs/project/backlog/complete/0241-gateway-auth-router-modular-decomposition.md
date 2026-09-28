---
id: '0241'
title: Gateway Auth Router Modular Decomposition
status: Complete
created: 2026-09-27
dependencies:
- TASK-0034
- TASK-0207
governing_adrs:
- ADR-0003
- ADR-0005
- ADR-0007
governing_prds:
- PRD-0023
governing_stories:
- US-0062
target_release: 0.7.0
pr_url: https://github.com/tyevans/runefoble/pull/268
---
# TASK-0241: Gateway Auth Router Modular Decomposition

## Status
Refined

## Summary
Decompose `gateway/api/src/gateway_api/routers/auth.py` (409 lines, 81.8% of limit - approaching the 500-line invariant) into modular submodules under `gateway/api/src/gateway_api/routers/auth/` (`schemas.py`, `registration.py`, `tokens.py`, and `dev_mail.py`), keeping all submodules strictly < 130 lines per Hard Invariant 6, ADR-0003, and ADR-0007.

## Problem Statement
`gateway/api/src/gateway_api/routers/auth.py` has grown to 409 lines, triggering a warning in the automated repository health scanner. It combines Pydantic request models (`RegisterRequest`, `TokenRequest`, `VerifyEmailRequest`, `DevSendEmailRequest`), user registration with Mailpit email verification workflows, OAuth2 token grant exchanges, in-memory development state storage, and Mailpit testing utility endpoints. As production Zitadel synchronization and password reset flows expand, this monolithic router will breach the 500-line limit unless decomposed into focused, single-responsibility submodules.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout and single-responsibility Python packages.
- **ADR-0005: Kubernetes-First Infrastructure with Helm and Kind**: Zitadel and Mailpit integration interfaces.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation between auth schemas, registration workflows, token issuance, and testing utilities.

## Detailed Specification & Implementation Plan
1. **Schemas Submodule (`gateway/api/src/gateway_api/routers/auth/schemas.py`)**:
   - Extract `RegisterRequest`, `TokenRequest`, `RefreshRequest`, `VerifyEmailRequest`, `DevSendEmailRequest`, `PasswordResetRequest`, and response models (< 100 lines).
2. **Registration Submodule (`gateway/api/src/gateway_api/routers/auth/registration.py`)**:
   - Extract `/register`, `/verify-email`, and `/resend-verification` endpoint handlers (< 120 lines).
3. **Tokens Submodule (`gateway/api/src/gateway_api/routers/auth/tokens.py`)**:
   - Extract `/token`, `/refresh`, and `/logout` OAuth2 token handlers (< 100 lines).
4. **Dev Testing Submodule (`gateway/api/src/gateway_api/routers/auth/dev_mail.py`)**:
   - Extract `/dev/emails`, `/dev/send-test`, `/dev/stats`, and client injection helper functions (< 100 lines).
5. **Aggregator Facade (`gateway/api/src/gateway_api/routers/auth/__init__.py`)**:
   - Combine sub-routers into a unified `APIRouter(prefix="/api/v1/auth", tags=["Authentication & Signups"])` maintaining 100% backward compatibility (< 50 lines).
6. **Verification**:
   - Run blackbox tests in `tests/test_blackbox_email_signup_mailpit.py` and `tests/test_blackbox_frontend_routing_and_auth.py`.

## INVEST Criteria Evaluation
- **Independent (I)**: Isolated to `gateway/api/src/gateway_api/routers/auth/` package decomposition.
- **Negotiable (N)**: HTTP API endpoints and response contracts are fully preserved.
- **Valuable (V)**: Eliminates 409-line health check warning and prevents Hard Invariant 6 breach.
- **Estimable (E)**: Pure refactoring of existing, well-tested route handlers.
- **Small (S)**: Scope strictly isolated to extracting router endpoints across 4 focused submodules (< 130 lines each).
- **Testable (T)**: Frontdoor validation via public HTTP endpoints (`/api/v1/auth/*`) in existing blackbox test suites.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Module Architecture**:
   - `gateway/api/src/gateway_api/routers/auth/` created with all submodules strictly < 130 lines each.
   - `gateway/api/src/gateway_api/routers/auth.py` replaced by the modular package with full backward compatibility.
2. **Frontdoor Verification**:
   - Zero health check warnings for gateway auth files.
   - All blackbox tests pass via `uv run pytest tests/test_blackbox_email_signup_mailpit.py` and `uv run pytest tests/test_blackbox_frontend_routing_and_auth.py`.
3. **Quality Gates**:
   - Formatted and linted cleanly via `uv run ruff check .` and `uv run ruff format --check .`.
