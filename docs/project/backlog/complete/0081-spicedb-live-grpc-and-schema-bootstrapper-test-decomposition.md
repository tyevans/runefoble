---
id: 0081
title: SpiceDB Live gRPC Client and Schema Bootstrapper Test Suite Modular Decomposition
status: Complete
created: 2026-09-26
dependencies:
- TASK-0035
governing_adrs:
- ADR-0001
- ADR-0005
- ADR-0007
- ADR-0009
target_release: 0.2.0
pr_url: https://github.com/tyevans/runefoble/pull/89
---
# TASK-0081: SpiceDB Live gRPC Client and Schema Bootstrapper Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_blackbox_spicedb_live.py` (306 lines, 61.2% of limit) into two specialized test modules (`tests/test_spicedb_schema_bootstrap.py` and `tests/test_blackbox_spicedb_live_grpc.py`) to prevent breaching Hard Invariant 6 (File length limit < 500 lines) as new schema relations (e.g. spectator cheer permissions, VTT asset access) are added.

## Problem Statement
`tests/test_blackbox_spicedb_live.py` covers two major capabilities introduced in TASK-0035:
1. Schema bootstrapping and migration: Loading `runefoble.zed`, compiling schema definitions, writing schema to SpiceDB, and validating fallback behavior when disconnected.
2. Live Zanzibar gRPC interactions: Dockerized SpiceDB testcontainer setup, relationship tuple writing, graph permission checking, dynamic relation revocations, and campaign role assignment REST endpoints (`POST /api/v1/campaigns/{id}/roles`).

As new permissions are added to `runefoble.zed` for upcoming milestones (lore knowledge base access, stream overlays, spectator participation), this test suite will expand and risk violating Hard Invariant 6.

## Governing Architecture & ADRs
- **ADR-0001: SpiceDB Zanzibar Object Authorization**: Live gRPC authorization evaluation.
- **ADR-0005: Kubernetes-First Infrastructure with Helm and Kind**: SpiceDB container configuration.
- **ADR-0007: Real-Time Voice and Board Synchronization**: Real-time permission checking.
- **ADR-0009: Continuous Backlog Refinement and Technical Debt Management**: Preemptive test splitting.

## Proposed Decomposition
1. **Schema Migration & Fallback Unit Suite (`tests/test_spicedb_schema_bootstrap.py`)**:
   - `bootstrap_schema()` with live and mock SpiceDB clients.
   - Schema file existence and syntax validation for `runefoble.zed`.
   - Disconnected/unreachable fallback mechanics (< 140 lines).
2. **Live Zanzibar Evaluation Blackbox Suite (`tests/test_blackbox_spicedb_live_grpc.py`)**:
   - Live testcontainer fixture and gRPC client connection.
   - Frontdoor campaign role assignment (`POST /api/v1/campaigns/{id}/roles`).
   - Zanzibar permission evaluation, tuple deletions, and revocation testing (< 180 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Modularizes test suite organization without changing production `runefoble_auth` or gateway route handlers.
- **Negotiable (N)**: Split boundaries between schema compilation and live gRPC test cases can be adjusted.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (< 500 lines) and allows fast schema bootstrap validation independent of Docker container availability.
- **Estimable (E)**: Clean separation between schema compilation tests and containerized gRPC integration tests.
- **Small (S)**: Scope strictly isolated to `tests/test_blackbox_spicedb_live.py`; all resulting files < 190 lines.
- **Testable (T)**: Verified with `uv run pytest tests/test_spicedb_schema_bootstrap.py tests/test_blackbox_spicedb_live_grpc.py`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. `tests/test_blackbox_spicedb_live.py` decomposed into focused test suites strictly under 200 lines each.
2. 100% test pass rate across all existing schema bootstrapping and live gRPC permission tests.
3. Conforms strictly to Hard Invariant 6 (< 500 lines per file).
4. Maintains blackbox frontdoor interactions via public HTTP endpoints and live SpiceDB gRPC client.
5. Passes `uv run ruff check` and `uv run ruff format --check`.
