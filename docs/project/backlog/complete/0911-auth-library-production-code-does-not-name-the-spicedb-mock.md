---
id: '0911'
title: Auth Library Production Code Does Not Name the SpiceDB Mock
status: Complete
created: 2026-11-19
dependencies: []
governing_adrs:
- ADR-0001
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: platform
target_release: 0.9.0
---
# TASK-0911: Auth Library Production Code Does Not Name the SpiceDB Mock

## Status
Complete

## Summary
The production SpiceDB modules in `libs/runefoble_auth` import their `Relationship` type from the mock package. The client factory and the sync service name `MockSpiceDBClient` in their types, and the sync health check detects the backend with `isinstance` on the mock and a read of a private attribute. Production code must not depend on a test double. This task adds one client port and moves the shared type out of the mock package.

## Problem Statement
- `libs/runefoble_auth/src/runefoble_auth/spicedb.py:21`, `grpc_adapter.py:18`, `sync_tuples.py:13`: `from runefoble_auth.mock.client import Relationship`.
- `libs/runefoble_auth/src/runefoble_auth/factory.py:9`, `:13`, `:32`: the cache `_client` and `set_spicedb_client` are typed `SpiceDBClient | MockSpiceDBClient`, but `get_spicedb_client` (`:16`) says it returns only `SpiceDBClient`.
- `libs/runefoble_auth/src/runefoble_auth/sync.py:10`, `:38`: the sync service is typed against the union. `:92-95`: `isinstance(self.spicedb, MockSpiceDBClient) and not getattr(self.spicedb, "_grpc_client", None)` sets the health `backend` field.

## Documentation & Architecture Review
- ADR-0015 problem 4 ("mock providers run in deployed environments") and decision (f).
- `docs/reference/spicedb-zitadel-identity-sync.md` documents the health reply. The four keys stay.
- TASK-0818 (complete) added the `set_spicedb_client` test seam. This task keeps the seam and types it against the port.
- DoR 9: no alias for `Relationship` in `mock/client.py`. Update the importers.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Move `Relationship` to `runefoble_auth/relationship.py`. Update every importer, the mock package included.
2. Add `runefoble_auth/port.py` with a `SpiceDBPort` Protocol. It lists only the methods that callers use (`check_permission`, `write_relationship`, `delete_relationship`, `read_relationships`, the batch and reconcile methods that `sync.py` and `sync_tuples.py` call) and a `backend_name: str` attribute.
3. `SpiceDBClient` sets `backend_name` from its transport (`"grpc"`). `MockSpiceDBClient` sets `"mock"`. Delete the `isinstance` probe and the `_grpc_client` read in `sync.py`.
4. Type `factory._client`, `get_spicedb_client` and `set_spicedb_client` against `SpiceDBPort`. Type the sync service against the port.
5. Service call sites keep compiling. TASK-0912 changes their annotations.

## Frontdoor Blackbox Test Plan
- The public sync health route returns the same four keys, with `backend: "grpc"` against the live SpiceDB fixture and `"mock"` when a test injects the mock through `set_spicedb_client`.
- `tests/test_blackbox_spicedb_single_client.py` and `tests/test_blackbox_spicedb_preshared_key.py` pass unchanged.
- Add one test that imports `runefoble_auth.spicedb`, `runefoble_auth.sync` and `runefoble_auth.factory` in a fresh interpreter and asserts that `runefoble_auth.mock` is not in `sys.modules`.

## Definition of Done
- No module outside `runefoble_auth/mock/` imports from `runefoble_auth.mock`.
- `docs/reference/spicedb-zitadel-identity-sync.md` names the port. `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `gateways-libs.md` (F1), `services-backend.md` (finding 1)
