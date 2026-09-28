---
id: '0242'
title: Platform Email Client Modular Decomposition
status: Refined
created: 2026-09-27
dependencies:
- TASK-0000
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

# TASK-0242: Platform Email Client Modular Decomposition

## Status
Refined

## Summary
Decompose `libs/runefoble_platform/src/runefoble_platform/email_client.py` (358 lines, 71.6% of limit) into modular submodules under `libs/runefoble_platform/src/runefoble_platform/email/` (`models.py`, `smtp.py`, and `mailpit.py`), keeping all submodules strictly < 130 lines per Hard Invariant 6 and ADR-0003.

## Problem Statement
`libs/runefoble_platform/src/runefoble_platform/email_client.py` was introduced to support local Mailpit email delivery and test verification for user signups. At 358 lines, it combines Pydantic email models (`EmailMessage`, `EmailRecipient`, `EmailVerificationPayload`), low-level SMTP client delivery with HTML MIME multipart composition, and HTTP REST client interactions with Mailpit's API (`/api/v1/messages`, message deletion, search). As transactional email templates (invites, password resets, campaign alerts) are added, this file will rapidly approach the 500-line invariant limit unless decoupled.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout in `libs/runefoble_platform/`.
- **ADR-0005: Kubernetes-First Infrastructure with Helm and Kind**: Mailpit mock SMTP service abstraction.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation between email data structures, SMTP transport, and Mailpit REST inspection.

## Detailed Specification & Implementation Plan
1. **Email Models Submodule (`libs/runefoble_platform/src/runefoble_platform/email/models.py`)**:
   - Extract email data structures, recipient schemas, verification token envelopes, and message summary models (< 100 lines).
2. **SMTP Transport Submodule (`libs/runefoble_platform/src/runefoble_platform/email/smtp.py`)**:
   - Extract async SMTP connection management, MIME multipart composition, and delivery routines (< 120 lines).
3. **Mailpit API Submodule (`libs/runefoble_platform/src/runefoble_platform/email/mailpit.py`)**:
   - Extract Mailpit REST API client methods for searching, inspecting, and purging test inboxes (< 110 lines).
4. **Platform Facade (`libs/runefoble_platform/src/runefoble_platform/email/__init__.py`)**:
   - Re-export `MailpitClient` and public functions maintaining 100% backward compatibility (< 40 lines).
5. **Verification**:
   - Verify tests in `tests/test_blackbox_email_signup_mailpit.py` pass without regression.

## INVEST Criteria Evaluation
- **Independent (I)**: Refactoring is strictly isolated to `libs/runefoble_platform/` email delivery modules.
- **Negotiable (N)**: `MailpitClient` public interface and behavior remain unchanged.
- **Valuable (V)**: Protects `libs/runefoble_platform/` against Hard Invariant 6 and separates transport from data models.
- **Estimable (E)**: Pure mechanical decomposition of existing Python functions and classes.
- **Small (S)**: Scope restricted to separating three distinct concerns (< 130 lines per file).
- **Testable (T)**: Frontdoor verification through Mailpit client tests and integration test suites.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Module Architecture**:
   - `libs/runefoble_platform/src/runefoble_platform/email/` created with all submodules strictly < 130 lines each.
   - `libs/runefoble_platform/src/runefoble_platform/email_client.py` refactored as a backward-compatible shim (< 40 lines).
2. **Frontdoor Verification**:
   - All email tests pass via `uv run pytest tests/test_blackbox_email_signup_mailpit.py`.
3. **Quality Gates**:
   - Formatted and linted cleanly via `uv run ruff check .` and `uv run ruff format --check .`.
