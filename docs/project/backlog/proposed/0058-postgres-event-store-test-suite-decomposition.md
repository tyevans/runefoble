---
id: '0058'
title: PostgreSQL Event Store and Provisioning Test Suite Modular Decomposition
status: Proposed
created: 2026-09-26
dependencies: [TASK-0036]
governing_adrs: [ADR-0005, ADR-0011]
target_release: 0.2.0
---

# TASK-0058: PostgreSQL Event Store and Provisioning Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_blackbox_postgres_event_store.py` (419 lines, 83.8% of limit) into modular test files (`tests/test_blackbox_postgres_provisioning.py` and `tests/test_blackbox_postgres_event_store.py` with shared fixtures) to prevent breaching Hard Invariant 6 (<500 lines per file).

## Problem Statement
`tests/test_blackbox_postgres_event_store.py` currently spans 419 lines. It bundles:
1. Docker container initialization and multi-database provisioning verification (`test_postgres_multidb_init_provisions_all_databases`).
2. DSN reconciliation, asyncpg dialect URL normalization, and reachability probe fallbacks (`test_normalize_async_postgres_url`, `test_is_database_reachable_and_fallback`).
3. Persistent event store table auto-creation, aggregate persistence/replay roundtrip across multiple bounded contexts, and optimistic concurrency control (`test_postgres_event_store_schema_creation_and_persistence_roundtrip`, `test_postgres_event_store_optimistic_locking_concurrency`).

As new multi-database and event store features are introduced, this file risks exceeding the 500-line hard ceiling.

## Proposed Decomposition
1. **Multi-Database & Connection Provisioning Suite (`tests/test_blackbox_postgres_provisioning.py`)**:
   - Docker container fixture and `init-multidb.sh` verification across zitadel, spicedb, and openpanel databases.
   - DSN normalization and database reachability probes (~180 lines).
2. **PostgreSQL Event Store Aggregate Persistence Suite (`tests/test_blackbox_postgres_event_store.py`)**:
   - Schema auto-creation.
   - Aggregate roundtrip persistence (`GameSessionAggregate`, `CharacterAggregate`, `BoardAggregate`).
   - Optimistic concurrency control tests (~200 lines).
3. **Shared Pytest Fixture Support**:
   - Extract `postgres_service` fixture into `tests/conftest.py` or dedicated test helper to eliminate container setup duplication.

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors test structure without changing production database scripts or event store code.
- **Negotiable (N)**: Split boundaries between provisioning and aggregate testing can be adjusted.
- **Valuable (V)**: Protects against Hard Invariant 6 violations and speeds up focused test execution.
- **Estimable (E)**: Straightforward pytest module decomposition.
- **Small (S)**: Scope strictly isolated to `tests/test_blackbox_postgres_event_store.py`.
- **Testable (T)**: `pytest tests/test_blackbox_postgres_*.py` executes all 6 tests with zero regressions.

## Acceptance Criteria
1. `tests/test_blackbox_postgres_event_store.py` and any new test files are strictly under 300 lines each.
2. 100% test pass rate across all provisioning, connection, and event store persistence test scenarios.
3. Conforms to Hard Invariant 6 (< 500 lines per file).
