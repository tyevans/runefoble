---
id: '0044'
title: SpiceDB Client Mock Separation and Auth Sync Test Suite Decomposition
status: Complete
created: 2026-09-26
dependencies:
- TASK-0008
- TASK-0016
- TASK-0032
governing_adrs:
- ADR-0001
- ADR-0005
- ADR-0007
- ADR-0008
- ADR-0009
target_release: 0.2.0
pr_url: https://github.com/tyevans/runefoble/pull/67
---
# TASK-0044: SpiceDB Client Mock Separation and Auth Sync Test Suite Decomposition

## Status
Refined

## Summary
Decompose `tests/test_blackbox_spicedb_zitadel_sync.py` (408 lines, 81.6% of limit) into two focused, modular test suites (`tests/test_blackbox_spicedb_identity_sync.py` and `tests/test_blackbox_spicedb_ownership_sync.py`) to prevent breaching Hard Invariant 6 (File length limit < 500 lines).

## Problem Statement
`tests/test_blackbox_spicedb_zitadel_sync.py` currently stands at 408 lines. It conflates several distinct authorization synchronization flows:
1. User registration, Zitadel OIDC identity claim syncing, and campaign GM/player role assignments (`test_user_registered_creates_user_subject`, `test_campaign_role_assigned_writes_spicedb_relationship`, `test_campaign_role_revoked_deletes_spicedb_relationship`).
2. Character aggregate ownership, campaign association, and permission checks (`test_character_created_writes_owner_relationship`, `test_character_ownership_revocation`).
3. Concurrent event handling, idempotent relationship writes, and dead-letter routing on malformed payloads (`test_idempotent_relationship_writes`, `test_malformed_event_handling`).

As fine-grained permissions for scenes, traps, and spectator feeds are added, this test suite will rapidly breach the 500-line ceiling.

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors test suite organization without modifying `runefoble_auth` core logic or Zanzibar schema.
- **Negotiable (N)**: Split boundaries between identity sync and resource ownership tests can be adjusted.
- **Valuable (V)**: Prevents hard invariant breaches, clarifies failure boundaries, and speeds up test parallelization.
- **Estimable (E)**: Pure test suite refactoring using existing mock fixtures.
- **Small (S)**: Scope strictly isolated to `tests/test_blackbox_spicedb_zitadel_sync.py`.
- **Testable (T)**: `uv run pytest tests/test_blackbox_spicedb_*.py` verifies 100% test pass rate with zero test regression.

## Governing Architecture & ADRs
- **ADR-0001**: SpiceDB Zanzibar Object-Level Authorization.
- **ADR-0005**: Kubernetes-First Infrastructure with Helm and Kind.
- **ADR-0007**: Development Tooling and Local Kind Cluster Workflows.
- **ADR-0008**: Property and Mutation Testing Strategy.
- **ADR-0009**: Code Quality and Linting with Ruff (strict file length invariant < 500 lines).

## Proposed Decomposition
1. **Identity & Campaign Role Sync Suite (`tests/test_blackbox_spicedb_identity_sync.py`)**:
   - User registration and OIDC subject mapping.
   - Campaign GM and player role assignments/revocations.
   - Idempotent relationship writes (< 220 lines).
2. **Resource Ownership & Edge Case Suite (`tests/test_blackbox_spicedb_ownership_sync.py`)**:
   - Character aggregate ownership and campaign relationship bindings.
   - Permission revocation races and malformed payload error handling (< 210 lines).
3. **Original Monolith Deletion**:
   - Remove `tests/test_blackbox_spicedb_zitadel_sync.py`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Modular Test Suite Creation**:
   - `tests/test_blackbox_spicedb_identity_sync.py` and `tests/test_blackbox_spicedb_ownership_sync.py` created.
   - Monolithic `tests/test_blackbox_spicedb_zitadel_sync.py` removed.
2. **Zero Coverage Loss**:
   - All existing test cases and assertions preserved without regressions.
3. **File Length Compliance**:
   - Both test files strictly under 250 lines each (well under the 500-line ceiling).
4. **Frontdoor Blackbox Verification**:
   - 100% pass rate on `uv run pytest tests/test_blackbox_spicedb_identity_sync.py tests/test_blackbox_spicedb_ownership_sync.py`.
5. **Quality Gate Verification**:
   - Passes `uv run ruff check tests/` and `uv run ruff format --check tests/`.
