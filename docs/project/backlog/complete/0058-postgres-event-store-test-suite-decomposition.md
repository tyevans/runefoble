---
id: 0058
title: PostgreSQL Event Store and Provisioning Test Suite Modular Decomposition
status: Complete
created: 2026-09-26
dependencies:
- TASK-0036
governing_adrs:
- ADR-0005
- ADR-0007
- ADR-0008
- ADR-0009
- ADR-0011
target_release: 0.2.0
pr_url: https://github.com/tyevans/runefoble/pull/62
---
# TASK-0058: PostgreSQL Event Store and Provisioning Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_blackbox_postgres_event_store.py` (419 lines, 83.8% of limit) into two modular test files (`tests/test_blackbox_postgres_provisioning.py` and `tests/test_blackbox_postgres_event_store.py` with shared container fixtures) to prevent breaching Hard Invariant 6 (File length limit < 500 lines).

## Problem Statement
`tests/test_blackbox_postgres_event_store.py` currently spans 419 lines. It bundles:
1. Docker container initialization, init scripts, and multi-database provisioning verification across Zitadel, SpiceDB, and OpenPanel databases (`test_postgres_multidb_init_provisions_all_databases`).
2. DSN reconciliation, asyncpg dialect URL normalization, and reachability probe fallbacks (`test_normalize_async_postgres_url`, `test_is_database_reachable_and_fallback`).
3. Persistent event store table auto-creation, aggregate persistence/replay roundtrip across multiple bounded contexts, and optimistic concurrency control (`test_postgres_event_store_schema_creation_and_persistence_roundtrip`, `test_postgres_event_store_optimistic_locking_concurrency`).

As new multi-database and event store features are introduced, this file risks exceeding the 500-line hard ceiling.

## INVEST Criteria Evaluation
- **Independent (I)**: Refactors test structure without changing production database scripts or event store code.
- **Negotiable (N)**: Split boundaries between provisioning and aggregate testing can be adjusted.
- **Valuable (V)**: Protects against Hard Invariant 6 violations and speeds up focused test execution.
- **Estimable (E)**: Straightforward pytest module decomposition.
- **Small (S)**: Scope strictly isolated to `tests/test_blackbox_postgres_event_store.py`.
- **Testable (T)**: `pytest tests/test_blackbox_postgres_*.py` executes all tests with zero regressions.

## Governing Architecture & ADRs
- **ADR-0005**: Kubernetes-First Infrastructure with Helm & Kind (PostgreSQL provisioning).
- **ADR-0007**: Development Tooling and Local Kind Cluster Workflows.
- **ADR-0008**: Property and Mutation Testing Strategy.
- **ADR-0009**: Code Quality and Linting with Ruff (strict file length invariant < 500 lines).
- **ADR-0011**: Event Sourcing with `eventsource-py` and PostgreSQL Event Store.

## Proposed Decomposition
1. **Multi-Database & Connection Provisioning Suite (`tests/test_blackbox_postgres_provisioning.py`)**:
   - Docker container fixture and `init-multidb.sh` verification across zitadel, spicedb, and openpanel databases.
   - DSN normalization and database reachability probes (~180 lines).
2. **PostgreSQL Event Store Aggregate Persistence Suite (`tests/test_blackbox_postgres_event_store.py`)**:
   - Schema auto-creation.
   - Aggregate roundtrip persistence (`GameSessionAggregate`, `CharacterAggregate`, `BoardAggregate`).
   - Optimistic concurrency control tests (~200 lines).
3. **Shared Pytest Fixture Support**:
   - Extract `postgres_service` fixture into shared fixture helper to eliminate container setup duplication.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Modular Test Suite Creation**:
   - `tests/test_blackbox_postgres_provisioning.py` created for multi-database initialization and connection probes.
   - `tests/test_blackbox_postgres_event_store.py` refactored to focus solely on schema creation, persistence roundtrips, and concurrency.
2. **Zero Coverage Loss**:
   - 100% of existing test assertions preserved and passing.
3. **File Length Compliance**:
   - Both test files strictly under 250 lines each (well under the 500-line hard invariant ceiling).
4. **Frontdoor Blackbox Verification**:
   - 100% pass rate on `uv run pytest tests/test_blackbox_postgres_provisioning.py tests/test_blackbox_postgres_event_store.py`.
5. **Quality Gate Verification**:
   - Passes `uv run ruff check tests/` and `uv run ruff format --check tests/`.
