---
id: '0036'
title: PostgreSQL Multi-Database Initialization & Persistent Event Store Connection
status: Complete
created: 2026-09-25
dependencies:
- TASK-0001
governing_adrs:
- ADR-0005
- ADR-0011
target_release: 0.1.0
pr_url: https://github.com/tyevans/runefoble/pull/14
---
# TASK-0036: PostgreSQL Multi-Database Initialization & Persistent Event Store Connection

## Status
Refined

## Summary
Update the PostgreSQL Helm deployment with an entrypoint initialization script (`init-multidb.sh`) that provisions dedicated databases for Zitadel (`zitadel`), SpiceDB (`spicedb`), and OpenPanel (`openpanel`) alongside the primary `runefoble` application database. Reconcile database configuration in `libs/runefoble_platform/src/runefoble_platform/event_sourcing.py` and `config.py` to correctly connect `PostgreSQLEventStore` via `database_url` with automatic table creation and graceful in-memory fallback.

## INVEST Criteria Evaluation
- **Independent (I)**: Solves the foundational database provisioning barrier required by platform identity, authorization, analytics, and persistence services without modifying domain aggregate logic.
- **Negotiable (N)**: Database naming conventions, connection pooling parameters (`pool_size`, `max_overflow`), and schema table names (`runefoble_events`) can be tuned via `PlatformSettings`.
- **Valuable (V)**: Prevents startup crash loops across Zitadel, SpiceDB, and OpenPanel containers in Kind/Kubernetes deployments; enables durable event sourcing beyond ephemeral in-memory storage.
- **Estimable (E)**: Standard Postgres `/docker-entrypoint-initdb.d/` shell script; straightforward DSN alignment with `eventsource-py`'s `PostgreSQLEventStore`.
- **Small (S)**: Limited to `deployments/helm/runefoble/templates/postgres.yaml` and `libs/runefoble_platform/src/runefoble_platform/event_sourcing.py`.
- **Testable (T)**: Frontdoor blackbox tests creating and saving domain aggregates against a PostgreSQL container instance, asserting that events are stored in `runefoble_events` table and accurately reconstituted.

## Governing Architecture & ADRs
- **ADR-0005**: Kubernetes-First Infrastructure with Helm and Kind (`postgres.yaml`).
- **ADR-0011**: Core Event Sourcing with `eventsource-py` (`PostgreSQLEventStore`).

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Multi-Database Init Script (`deployments/helm/runefoble/templates/postgres.yaml`)**:
   - Add ConfigMap containing `/docker-entrypoint-initdb.d/init-multidb.sh` creating `zitadel`, `spicedb`, and `openpanel` databases with permissions granted to the default user.
2. **Platform Event Store DSN Reconciliation (`libs/runefoble_platform/src/runefoble_platform/event_sourcing.py`)**:
   - Reconcile `PlatformSettings` so `get_event_store()` reads `settings.database_url` (or clean async/sync driver DSN conversion) and checks `settings.use_postgres_event_store`.
3. **Blackbox TDD Suite (`tests/test_blackbox_postgres_event_store.py`)**:
   - Test verifying `PostgreSQLEventStore` successfully writes domain events and replays aggregate state, with fallback to `InMemoryEventStore` when offline.
4. **File Invariant Check**:
   - All touched files remain strictly under 500 lines.
