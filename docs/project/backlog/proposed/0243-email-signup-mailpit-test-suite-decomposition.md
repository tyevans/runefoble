---
id: '0243'
title: Email Signup Mailpit Blackbox Test Suite Decomposition
status: Proposed
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
---

# TASK-0243: Email Signup Mailpit Blackbox Test Suite Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_blackbox_email_signup_mailpit.py` (347 lines, 69.4% of limit) into focused test modules under `tests/test_blackbox_email_signup_mailpit/` (`test_registration_flow.py`, `test_token_exchange.py`, and `test_dev_mailpit_api.py`), keeping all test files strictly < 150 lines per Hard Invariant 6 and Hard Invariant 7.

## Problem Statement
`tests/test_blackbox_email_signup_mailpit.py` exercises end-to-end user registration, email verification token extraction via Mailpit REST API, token exchange grants, rate-limiting, and mock SMTP failure handling in a single 347-line test suite. As additional authentication integration tests (password reset flows, multi-tenant email domains, invite claims) are added, this test suite will approach the 500-line invariant limit unless decoupled.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean test module organization.
- **ADR-0005: Kubernetes-First Infrastructure with Helm and Kind**: Mailpit mock SMTP service verification.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation across test suites.

## Scope of Work
1. **Registration & Verification Test Submodule (`tests/test_blackbox_email_signup_mailpit/test_registration_flow.py`)**:
   - Test user registration, verification email receipt in Mailpit, code validation, and duplicate registration errors (< 130 lines).
2. **Token Exchange Test Submodule (`tests/test_blackbox_email_signup_mailpit/test_token_exchange.py`)**:
   - Test password token grant, refresh token flow, invalid credentials, and unverified account blocking (< 120 lines).
3. **Dev Mailpit Utilities Test Submodule (`tests/test_blackbox_email_signup_mailpit/test_dev_mailpit_api.py`)**:
   - Test development endpoints (`/dev/emails`, `/dev/send-test`, `/dev/stats`) and inbox clearing (< 110 lines).
4. **Verification**:
   - Run the decomposed test suite via `uv run pytest tests/test_blackbox_email_signup_mailpit/`.

## Definition of Done
- `tests/test_blackbox_email_signup_mailpit/` created with all modules strictly < 150 lines each.
- `tests/test_blackbox_email_signup_mailpit.py` cleanly replaced.
- All test scenarios pass with zero regressions.
- Linting and formatting pass via `uv run ruff check .` and `uv run ruff format --check .`.
