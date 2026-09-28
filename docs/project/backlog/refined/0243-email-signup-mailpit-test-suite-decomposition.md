---
id: '0243'
title: Email Signup Mailpit Blackbox Test Suite Decomposition
status: Refined
created: 2026-09-27
dependencies:
- TASK-0034
- TASK-0207
governing_adrs:
- ADR-0003
- ADR-0005
- ADR-0007
- ADR-0010
- ADR-0013
governing_prds:
- PRD-0023
governing_stories:
- US-0062
target_release: 0.7.0
---

# TASK-0243: Email Signup Mailpit Blackbox Test Suite Decomposition

## Status
Refined

## Summary
Decompose `tests/test_blackbox_email_signup_mailpit.py` (347 lines, 69.4% of limit) into focused test modules under `tests/test_blackbox_email_signup_mailpit/` (`conftest.py`, `test_registration_flow.py`, `test_token_exchange.py`, and `test_dev_mailpit_api.py`), keeping all test files strictly < 150 lines per Hard Invariant 6 and Hard Invariant 7.

## Problem Statement
`tests/test_blackbox_email_signup_mailpit.py` exercises end-to-end user registration, email verification token extraction via Mailpit REST API, token exchange grants, rate-limiting, and mock SMTP failure handling in a single 347-line test suite. As additional authentication integration tests (password reset flows, multi-tenant email domains, invite claims) are added, this test suite will approach the 500-line invariant limit unless decoupled into focused sub-suites.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/test-email-signups-with-mailpit.md`: Capturing and verifying email signups and verification links with Mailpit mock SMTP.
  - `docs/how-to/authenticate-with-zitadel-oidc.md`: OIDC token verification and user registration.
- **Governing Architecture & ADRs**:
  - **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean test module layout.
  - **ADR-0005: Kubernetes-First Infrastructure with Helm and Kind**: Mailpit mock SMTP service verification.
  - **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation across test suites.
  - **ADR-0010: Continuous Integration Pipeline**: Rapid regression feedback.
  - **ADR-0013: Modular Decomposition**: All test modules kept strictly < 150 lines.

## Product & User Story References
- Technical debt refactoring supporting:
  - [`prd-0023-unified-frontend-application-shell-and-campaign-hub.md`](../../product/accepted/prd-0023-unified-frontend-application-shell-and-campaign-hub.md)
  - [`us-0062-user-signup-and-zitadel-authentication.md`](../../user_stories/accepted/us-0062-user-signup-and-zitadel-authentication.md)

## Detailed Specification & Implementation Plan
1. **Shared Fixtures Submodule (`tests/test_blackbox_email_signup_mailpit/conftest.py`)**:
   - Extract test client setup, Mailpit mock API client, and clean inbox fixtures (< 60 lines).
2. **Registration & Verification Test Submodule (`tests/test_blackbox_email_signup_mailpit/test_registration_flow.py`)**:
   - Test user registration, verification email receipt in Mailpit, code validation, and duplicate registration errors (< 120 lines).
3. **Token Exchange Test Submodule (`tests/test_blackbox_email_signup_mailpit/test_token_exchange.py`)**:
   - Test password token grant, refresh token flow, invalid credentials, and unverified account blocking (< 110 lines).
4. **Dev Mailpit Utilities Test Submodule (`tests/test_blackbox_email_signup_mailpit/test_dev_mailpit_api.py`)**:
   - Test development endpoints (`/dev/emails`, `/dev/send-test`, `/dev/stats`) and inbox clearing (< 110 lines).
5. **Verification**:
   - Run the decomposed test suite via `uv run pytest tests/test_blackbox_email_signup_mailpit/`.

## INVEST Criteria Evaluation
- **Independent (I)**: Test modularization that does not affect production code.
- **Negotiable (N)**: Submodule division can be tuned across registration, tokens, and dev utilities.
- **Valuable (V)**: Protects email signup test suite (347 lines) from exceeding the 500-line invariant.
- **Estimable (E)**: Pure extraction of test functions into dedicated modules.
- **Small (S)**: Each extracted test file strictly < 150 lines.
- **Testable (T)**: Self-testing; test suite must execute cleanly with 100% pass rate.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `tests/test_blackbox_email_signup_mailpit/` created and root test file cleanly removed.
2. All extracted test submodules strictly < 150 lines each per Hard Invariant 6.
3. All test scenarios pass with zero regressions via `uv run pytest tests/test_blackbox_email_signup_mailpit/`.
4. Linting and formatting pass via `uv run ruff check .` and `uv run ruff format --check .`.
