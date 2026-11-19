---
id: '0486'
title: Remove Backward Compatibility Shims & Re-exports in runefoble_auth
status: Complete
created: 2026-09-29
dependencies:
- TASK-0034
- TASK-0520
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
Complete

Audit 2026-11-17: class names corrected. The auth shim items depend on TASK-0520. The `verify_token` method is not removed.

## Summary
Excise all legacy token verification wrappers, backward-compatibility methods, and re-export aliases from `libs/runefoble_auth` (the unverified `decode_token` path, which TASK-0520 removes; `ZitadelAuthService.verify_token` is canonical and stays), migrating all callers directly to authoritative async verification methods.

## Problem Statement
In `libs/runefoble_auth/src/runefoble_auth/zitadel.py`, `verify_token` (line 153) is the canonical verification method (audit 2026-11-17: it is not a legacy shim). Retaining legacy synchronous verification wrappers or fallback stubs in authorization modules clutters security boundaries and violates the DoR zero backward compatibility mandate.

## Documentation & Architecture Review
- **Documentation Consulted**:
  - `docs/how-to/authenticate-with-zitadel-oidc.md`: Canonical Zitadel OIDC token verification.
  - `docs/how-to/define-spicedb-zanzibar-permissions.md`: SpiceDB Zanzibar client integration.
- **Governing Architecture & ADRs**:
  - **ADR-0001: Google Zanzibar for Fine-Grained Authorization**: SpiceDB client schema.
  - **ADR-0002: Zitadel OIDC Identity Provider**: OIDC token decoding and JWKS validation.

## Product & User Story References
- `prd-0001-runefoble-platform-foundations.md`
- `us-0010-developer-local-infrastructure-and-test-tooling.md`

## Detailed Specification & Implementation Plan
1. **Remove Legacy Compatibility Methods in `zitadel.py`**:
   - Inspect `libs/runefoble_auth/src/runefoble_auth/zitadel.py`. Keep `ZitadelAuthService.verify_token`. Remove `decode_token` only as TASK-0520 specifies.
   - Ensure `ZitadelAuthService` exposes one canonical verification method. The names `ZitadelAuthClient`, `verify_token_async`, and `UserTokenClaims` do not exist in the code (audit 2026-11-17).
2. **Clean Up `__init__.py` Re-exports**:
   - Inspect `libs/runefoble_auth/src/runefoble_auth/__init__.py` (removed) to ensure only authoritative classes that exist (`ZitadelAuthService`, `SpiceDBClient`) are exposed, removing any deprecated alias symbols.
3. **Migrate Call Sites Across Workspace**:
   - Audit `gateway/api`, services, and tests for any calls to legacy `verify_token` shims and update them to use canonical interfaces.
4. **Update Test Assertions**:
   - Verify all auth blackbox tests in `tests/test_blackbox_webrtc_auth.py` and `tests/test_spicedb_zitadel_sync.py` (removed) pass without reliance on deprecated methods.

## INVEST Criteria Evaluation
- **Independent (I)**: Changes are strictly self-contained within auth library and caller interfaces.
- **Negotiable (N)**: Clean unification of async verification methods.
- **Valuable (V)**: Hardens authentication pipeline and eliminates dead code.
- **Estimable (E)**: Scoped to `zitadel.py`, `__init__.py`, and direct callers.
- **Small (S)**: Clean edits under 50 lines.
- **Testable (T)**: Verified via `uv run pytest tests/test_blackbox_auth*` and auth test suite.

## Definition of Done
1. `zitadel.py` legacy backward-compatibility methods removed.
2. `libs/runefoble_auth/__init__.py` (removed) cleaned of any deprecated alias symbols.
3. All service and gateway callers migrated to canonical auth methods.
4. `uv run pytest` passes cleanly with zero deprecation warnings from auth.
5. Code passes `uv run ruff check .` and file length remains < 500 lines.

## Orchestrator Addenda (2026-11-17)

Source: `.audit/synth/discovered-round1.md`.

- `libs/runefoble_auth/src/runefoble_auth/mock_spicedb.py` (removed) is a facade re-export with `__all__`. Delete it and update the callers.

## Orchestrator Addenda (2026-11-17, round 2)

Source: `.audit/synth/discovered-round2.md`.

- tests/test_blackbox_settlements_integration/test_invariants_and_compat.py::test_auth_backwards_compatibility_exports checks re-exports of the auth package. Delete the test with the re-exports it checks.
