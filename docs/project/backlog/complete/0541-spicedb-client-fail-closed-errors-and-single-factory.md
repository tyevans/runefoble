---
id: '0541'
title: SpiceDB Client Fail-Closed Errors and Single Factory
status: Complete
created: 2026-11-17
dependencies:
- TASK-0520
- TASK-0625
- TASK-0540
governing_adrs:
- ADR-0001
- ADR-0007
governing_prds: []
governing_stories:
- US-0013
target_release: 0.9.0
---

# TASK-0541: SpiceDB Client Fail-Closed Errors and Single Factory

## Status
Complete

## Summary
The SpiceDB client in `libs/runefoble_auth` turns errors into silent results. A transport failure or an undefined name is returned as `False`, or it is swallowed by `contextlib.suppress(Exception)`. Eleven service-local factories copy the client setup, and some of them read a setting that does not exist. This task makes the shared client fail closed. It adds one cached factory in the library, and it leaves the claim sync path to TASK-0534, which removes grants from token claims. Services delete their own factory copies in their owning tasks.

## Problem Statement
- `libs/runefoble_auth/src/runefoble_auth/spicedb.py` and `grpc_adapter.py` return the check result only. Callers cannot tell "denied" from "SpiceDB is down" or "name is not in the schema" (`w3-authz-coverage.md` F16, F17).
- `grpc_adapter.py:147` maps `gm` to `game_master` on the check side only. Writes use `gm`, so writes and checks disagree.
- Claim sync (`libs/runefoble_auth/src/runefoble_auth/sync.py`, `sync_tuples.py`) turns token roles and `is_admin` into campaign grants. TASK-0534 deletes that path. This task does not change it.
- `gateway/api/src/gateway_api/auth.py:23-37` seeds fixed tuples into the mock client when `spicedb_endpoint == "mock"`. That is test wiring in the production gateway (`w1-libs.md` F11).
- Eleven `def get_spicedb_client` copies exist. Direct `SpiceDBClient()` calls exist in `routers/auth/admin.py:18` and `routers/auth/registration.py:22` (`w3-ddd-architecture.md` F15).
- The Watcher factory reads `spicedb_token`, which does not exist. It raises `AttributeError` (`w3-ddd-architecture.md` F8).

## Documentation & Architecture Review
- ADR-0001: SpiceDB is the only object-permission authority. A check that cannot be answered must not return "allowed" or "denied" by accident.
- ADR-0007: the library owns the client. Bounded contexts consume it through one factory.
- `docs/reference/platform-services.md` documents the SpiceDB endpoint and key variables. Update it for the typed errors.
- `docs/how-to/authenticate-with-zitadel-oidc.md` describes the claim sync. Update it to say that grants come from verified principals only (TASK-0520 defines the principal type).

## Product & User Story References
- US-0013 (gateway Zanzibar authorization): a denied or failed check must not grant access.
- US-0009 (campaign access control).

## Detailed Specification & Implementation Plan
1. Typed errors in `libs/runefoble_auth/src/runefoble_auth/errors.py`:
   - `AuthzUnavailableError` for gRPC `UNAVAILABLE`, `DEADLINE_EXCEEDED`, and connection errors.
   - `AuthzSchemaError` for `INVALID_ARGUMENT` and `FAILED_PRECONDITION` (undefined type, relation, or permission).
   - `AuthzWriteError` for any failed write or delete.
   Each error keeps the original gRPC status in its message. Each error subclasses one base `AuthzError`.
2. `SpiceDBClient.check_permission` raises the typed errors. It never returns `False` for a transport or schema error. It returns `False` only for `NO_PERMISSION`.
3. `write_relationship`, `touch_relationship`, `delete_relationship`, `write_schema` raise `AuthzWriteError`. No caller may wrap them in `suppress`.
4. Remove the `gm` to `game_master` special case in `grpc_adapter.py`. Callers pass schema names. A write that names `gm` raises `AuthzSchemaError`.
   `owner -> owner`, `dm` and `dungeon_master` -> `dungeon_master`, `gm` and `game_master` -> `game_master`, `player` -> `player`, `spectator` -> `spectator`.
5. Add `libs/runefoble_auth/src/runefoble_auth/factory.py` with `get_spicedb_client()`. It caches one `SpiceDBClient` built from `PlatformSettings.spicedb_preshared_key` (TASK-0625). It raises `ConfigurationError` when the key is missing outside test mode.
6. Remove the mock wiring from `gateway/api/src/gateway_api/auth.py:23-37`. The gateway uses the factory only. Tests inject a mock through their own fixture (TASK-0542).
7. `bootstrap_schema.py`: remove the default `"secret"` token (TASK-0625 owns the setting; this task makes the function require an explicit token).
8. Do not edit service-local factories in this task. Each owning bounded-context task (TASK-0546 to TASK-0558) deletes its own copy and imports the library factory.

## Frontdoor Blackbox Test Plan
- Library unit tests (no HTTP): a fake gRPC stub raises `UNAVAILABLE`. `check_permission` must raise `AuthzUnavailableError`. It must not return `False`. Before the fix it returns `False`.
- A fake stub returns `INVALID_ARGUMENT` for an undefined permission. `check_permission` raises `AuthzSchemaError`.
- A fake stub fails a `WriteRelationships` call. `write_relationship` raises `AuthzWriteError`.

## Definition of Done
1. `errors.py` and `factory.py` exist. The library factory is the only `SpiceDBClient` constructor used in `libs/` and `gateway/api/src/gateway_api/auth.py`.
2. No `suppress(Exception)` wraps a SpiceDB write in `libs/` or in `gateway/api/src/gateway_api/auth.py`.
3. `grep -rn "'gm'\|\"gm\"" libs/runefoble_auth/src` shows no write of `gm` to a relation.
4. Unit tests listed in the frontdoor plan pass in `libs/runefoble_auth/tests/`.
5. `uv run pytest libs/runefoble_auth` passes.
6. `docs/reference/platform-services.md` and the Zitadel how-to match the new behaviour.
7. No file in the change exceeds 500 lines.

## Audit Provenance

- Severity: high
- Source audits: `w3-authz-coverage.md`, `w3-ddd-architecture.md`, `w1-libs.md`, `w2-rules-compendium.md`, `w2-voice-agent.md`

## Orchestrator Addenda (2026-11-17, refactor-r1)

- TASK-0541: append "Also remove `contextlib.suppress(Exception)` around SpiceDB setters in `tests/conftest.py:170-183`; task 0714 owns the test side." (cross-reference only)
