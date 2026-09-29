---
id: '0486'
title: Remove Backward Compatibility Shims & Re-exports in runefoble_auth
status: Refined
created: 2026-09-29
dependencies:
- TASK-0034
governing_adrs:
- ADR-0001
- ADR-0002
governing_prds:
- PRD-0001
governing_stories:
- US-0010
target_release: 0.9.0
---

# TASK-0486: Remove Backward Compatibility Shims & Re-exports in runefoble_auth

## Status
Refined

## Summary
Excise all legacy token verification wrappers, backward-compatibility methods, and re-export aliases from `libs/runefoble_auth` (specifically legacy sync `verify_token` shims in `zitadel.py`), migrating all callers directly to authoritative async verification methods.

## Problem Statement
In `libs/runefoble_auth/src/runefoble_auth/zitadel.py`, a legacy `verify_token` method exists purely for backward compatibility, wrapping the underlying verification logic. Retaining legacy synchronous verification wrappers or fallback stubs in authorization modules clutters security boundaries and violates the DoR zero backward compatibility mandate.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/authenticate-with-zitadel-oidc.md`: Canonical Zitadel OIDC token verification.
  - `docs/how-to/define-spicedb-zanzibar-permissions.md`: SpiceDB Zanzibar client integration.
- **Governing Architecture & ADRs**:
  - **ADR-0001: Google Zanzibar for Fine-Grained Authorization**: SpiceDB client schema.
  - **ADR-0002: Zitadel OIDC Identity Provider**: OIDC token decoding and JWKS validation.

## Product & User Story References
- [`prd-0001-runefoble-platform-foundations.md`](../../product/accepted/prd-0001-runefoble-platform-foundations.md)
- [`us-0010-developer-local-infrastructure-and-test-tooling.md`](../../user_stories/accepted/us-0010-developer-local-infrastructure-and-test-tooling.md)

## Detailed Specification & Implementation Plan
1. **Remove Legacy Compatibility Methods in `zitadel.py`**:
   - Inspect `libs/runefoble_auth/src/runefoble_auth/zitadel.py` and remove legacy `verify_token` backward-compatibility aliases and docstrings.
   - Ensure `ZitadelAuthClient` exposes only canonical `verify_token_async` (or the unified async verification method).
2. **Clean Up `__init__.py` Re-exports**:
   - Inspect `libs/runefoble_auth/src/runefoble_auth/__init__.py` to ensure only authoritative classes (`ZitadelAuthClient`, `SpiceDBClient`, `UserTokenClaims`) are exposed, removing any deprecated alias symbols.
3. **Migrate Call Sites Across Workspace**:
   - Audit `gateway/api`, services, and tests for any calls to legacy `verify_token` shims and update them to use canonical interfaces.
4. **Update Test Assertions**:
   - Verify all auth blackbox tests in `tests/test_blackbox_webrtc_auth.py` and `tests/test_spicedb_zitadel_sync.py` pass without reliance on deprecated methods.

## INVEST Criteria Evaluation
- **Independent (I)**: Changes are strictly self-contained within auth library and caller interfaces.
- **Negotiable (N)**: Clean unification of async verification methods.
- **Valuable (V)**: Hardens authentication pipeline and eliminates dead code.
- **Estimable (E)**: Scoped to `zitadel.py`, `__init__.py`, and direct callers.
- **Small (S)**: Clean edits under 50 lines.
- **Testable (T)**: Verified via `uv run pytest tests/test_blackbox_auth*` and auth test suite.

## Definition of Done
1. `zitadel.py` legacy backward-compatibility methods removed.
2. `libs/runefoble_auth/__init__.py` cleaned of any deprecated alias symbols.
3. All service and gateway callers migrated to canonical auth methods.
4. `uv run pytest` passes cleanly with zero deprecation warnings from auth.
5. Code passes `uv run ruff check .` and file length remains < 500 lines.
