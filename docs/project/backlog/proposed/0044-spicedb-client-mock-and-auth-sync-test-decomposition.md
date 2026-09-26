---
id: '0044'
title: SpiceDB Client Mock Separation and Auth Sync Test Suite Decomposition
status: Proposed
created: 2026-09-26
dependencies: [TASK-0008, TASK-0016, TASK-0032]
governing_adrs: [ADR-0001, ADR-0005, ADR-0007]
target_release: 0.2.0
---

# TASK-0044: SpiceDB Client Mock Separation and Auth Sync Test Suite Decomposition

## Status
Proposed

## Summary
Decompose `libs/runefoble_auth/src/runefoble_auth/spicedb.py` (409 lines) and its blackbox integration test suite `tests/test_blackbox_spicedb_zitadel_sync.py` (408 lines) into single-responsibility modules to stay well clear of Hard Invariant 6 (File length limit < 500 lines).

## Problem Statement
Health checks highlight two authorization-related files that have grown past 400 lines:
- `libs/runefoble_auth/src/runefoble_auth/spicedb.py` (409 lines, 81.8% of limit): Bundles `Relationship` schema structures, the comprehensive in-memory `MockSpiceDBClient` (parsing relations, wildcards, caveats, subject sets), and the production gRPC client wrapper in a single file.
- `tests/test_blackbox_spicedb_zitadel_sync.py` (408 lines, 81.6% of limit): Conflates user identity claim syncing, campaign GM/player role assignments, character ownership propagation, and revocation race conditions in one monolithic test file.

## Proposed Decomposition
1. **Mock Client Separation (`libs/runefoble_auth/src/runefoble_auth/`)**:
   - Extract `MockSpiceDBClient` to `mock_spicedb.py` (< 230 lines).
   - Retain `Relationship`, `SpiceDBClient`, and clean re-exports in `spicedb.py` (< 190 lines).
   - Re-export `MockSpiceDBClient` from `runefoble_auth` so existing imports remain backward-compatible.
2. **Auth Sync Test Decomposition (`tests/`)**:
   - `tests/test_blackbox_spicedb_identity_sync.py`: User registration, identity claims, and campaign role bindings (< 220 lines).
   - `tests/test_blackbox_spicedb_ownership_sync.py`: Character aggregate ownership, campaign association, and permission revocation (< 210 lines).

## Acceptance Criteria
1. Zero breaking changes to `runefoble_auth` public APIs (`SpiceDBClient`, `MockSpiceDBClient`, `Relationship`).
2. All modified and new files strictly under 250 lines.
3. 100% test pass rate on `uv run pytest tests/test_blackbox_spicedb*.py` and `uv run ruff check .`.
