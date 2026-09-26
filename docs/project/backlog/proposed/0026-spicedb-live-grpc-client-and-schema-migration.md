---
id: 0026
title: Live SpiceDB gRPC Client Integration & Schema Migration Bootstrapper
status: Proposed
created: 2026-09-25
dependencies: [TASK-0008, TASK-0016]
governing_adrs: [ADR-0001, ADR-0005, ADR-0007]
target_release: 0.1.0
---

# TASK-0026 — Live SpiceDB gRPC Client Integration & Schema Migration Bootstrapper

## Summary
Connect `SpiceDBClient` in `libs/runefoble_auth` to the live self-hosted SpiceDB gRPC service using the official `authzed` SDK. Implement live relationship creation, deletion, and checks against the Zanzibar engine while preserving seamless fallback to in-memory mock tuples for disconnected unit tests. Provide a Helm pre-install/upgrade job that compiles and applies `libs/runefoble_auth/schema/runefoble.zed` to SpiceDB during cluster deployment.

## INVEST Criteria Evaluation
- **Independent (I)**: Enhances the internal transport of `SpiceDBClient` without modifying the public API contracts established in `TASK-0008` (`require_zanzibar_permission`) or `TASK-0016` (`WebSocketActionValidator`).
- **Negotiable (N)**: Schema deployment method (Kubernetes Job vs initContainer vs Python startup check) and connection retry/backoff policies are negotiable.
- **Valuable (V)**: Fulfills Hard Invariant 1 in production: ensures fine-grained object-level authorization is enforced by a resilient Zanzibar graph database rather than transient process memory.
- **Estimable (E)**: SpiceDB gRPC API (`WriteRelationships`, `DeleteRelationships`, `CheckPermission`) is well-documented and covered by ADR-0001.
- **Small (S)**: Confined to `libs/runefoble_auth/src/runefoble_auth/spicedb.py`, `pyproject.toml`, and a Helm migration template.
- **Testable (T)**: Frontdoor blackbox tests via Gateway endpoints asserting relationship writing and permission evaluation against both mock client and live test container.

## Governing Architecture & ADRs
- **ADR-0001**: SpiceDB Zanzibar Object-Level Authorization.
- **ADR-0005**: Kubernetes-First Infrastructure with Helm and Kind (`spicedb.yaml`).

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Official Client Dependency**:
   - Add `authzed>=1.15.0` to `libs/runefoble_auth/pyproject.toml`.
2. **Live gRPC Client Implementation (`libs/runefoble_auth/src/runefoble_auth/spicedb.py`)**:
   - Complete `write_relationship`, `delete_relationship`, and `check_permission` using `authzed.api.v1.Client`.
   - Implement resilient fallback to `MockSpiceDBClient` when `use_mock=True` or when the gRPC server is unreachable.
3. **Schema Bootstrapper**:
   - Create schema migration script / Helm job (`deployments/helm/runefoble/templates/spicedb-schema-job.yaml`) that executes `zed schema write` using `libs/runefoble_auth/schema/runefoble.zed`.
4. **Blackbox TDD Suite (`tests/test_blackbox_spicedb_live.py`)**:
   - Frontdoor tests assigning campaign roles via Gateway API (`POST /api/v1/campaigns/{id}/roles`), verifying SpiceDB relationship tuples persist and correctly govern permission checks.
5. **File Invariant Check**:
   - All touched files remain strictly under 500 lines.
