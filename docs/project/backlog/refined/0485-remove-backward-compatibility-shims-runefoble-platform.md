---
id: '0485'
title: Remove Backward Compatibility Shims & Re-exports in runefoble_platform
status: Refined
created: 2026-09-29
dependencies:
- TASK-0242
governing_adrs:
- ADR-0003
- ADR-0006
governing_prds:
- PRD-0001
governing_stories:
- US-0010
target_release: 0.9.0
---

# TASK-0485: Remove Backward Compatibility Shims & Re-exports in runefoble_platform

## Status
Refined

## Summary
Purge all backward-compatibility shims, deprecated facades, and re-export aliases from `libs/runefoble_platform` (`email_client.py`, `analytics_client.py`, `analytics_privacy.py`, and `database_url` in `config.py`), updating all internal call sites and blackbox tests directly to authoritative submodules.

## Problem Statement
During past modular refactorings of the platform foundation (such as email client extraction and analytics modularization), transitional shims (`email_client.py`, `analytics_client.py`, `analytics_privacy.py`) and configuration aliases (`database_url` for `postgres_url`) were preserved for backward compatibility. Because Runefoble is pre-production with zero active external users, retaining these compatibility artifacts creates maintenance overhead and violates the Definition of Ready (DoR) zero-shim policy.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/reference/architecture-overview.md`: `runefoble_platform` foundation library.
  - `docs/how-to/test-email-signups-with-mailpit.md`: Authoritative `runefoble_platform.email` imports.
  - `docs/how-to/track-analytics-events.md`: Authoritative `runefoble_platform.analytics` imports.
- **Governing Architecture & ADRs**:
  - **ADR-0003: UV Monorepo Workspace**: Clean boundaries between workspace packages without legacy wrappers.
  - **ADR-0006: Redis Streams Distributed Domain Event Streaming**: Core event bus models.

## Product & User Story References
- [`prd-0001-runefoble-platform-foundations.md`](../../product/accepted/prd-0001-runefoble-platform-foundations.md)
- [`us-0010-developer-local-infrastructure-and-test-tooling.md`](../../user_stories/accepted/us-0010-developer-local-infrastructure-and-test-tooling.md)

## Detailed Specification & Implementation Plan
1. **Delete Backward-Compatibility Shims**:
   - Remove `libs/runefoble_platform/src/runefoble_platform/email_client.py`.
   - Remove `libs/runefoble_platform/src/runefoble_platform/analytics_client.py`.
   - Remove `libs/runefoble_platform/src/runefoble_platform/analytics_privacy.py`.
2. **Remove Configuration Aliases**:
   - In `libs/runefoble_platform/src/runefoble_platform/config.py`, remove the `database_url` backward-compatibility alias property; callers must use `postgres_url` directly.
3. **Direct Call Site Migration**:
   - Audit and migrate any callers importing from `runefoble_platform.email_client` or `runefoble_platform.analytics_client` across `gateway/api`, `services/`, and tests to `runefoble_platform.email` and `runefoble_platform.analytics`.
4. **Update Blackbox Test Suites**:
   - In `tests/test_platform_email_modular_decomposition.py`, remove `test_import_from_backward_compatibility_shim()` and test strictly through `runefoble_platform.email`.
   - Ensure all platform unit and blackbox tests pass cleanly.

## INVEST Criteria Evaluation
- **Independent (I)**: Isolated strictly to `libs/runefoble_platform` and direct consumers.
- **Negotiable (N)**: Implementation details focus on clean deprecation and deletion.
- **Valuable (V)**: Cleans technical debt and establishes a zero-shim baseline for core libraries.
- **Estimable (E)**: Clearly identified four files to remove or modify.
- **Small (S)**: File changes under 100 lines across 3 files, well under the 500-line invariant.
- **Testable (T)**: Verified via `uv run pytest tests/test_platform_email_modular_decomposition.py` and workspace test suite.

## Definition of Done
1. `libs/runefoble_platform/src/runefoble_platform/email_client.py` deleted.
2. `libs/runefoble_platform/src/runefoble_platform/analytics_client.py` and `analytics_privacy.py` deleted.
3. `database_url` alias removed from `runefoble_platform.config`.
4. All workspace call sites migrated to authoritative imports.
5. All backward-compatibility shim tests removed and updated.
6. `uv run pytest` passes and `make lint` reports zero issues.
