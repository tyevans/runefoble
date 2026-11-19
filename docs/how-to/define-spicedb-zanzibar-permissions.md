# How-To: Define and Check SpiceDB Zanzibar Permissions

## Overview
Runefoble enforces fine-grained, object-level authorization across campaigns, game sessions, characters, and tactical boards using **SpiceDB** (a Google Zanzibar-inspired graph permission system).

All permission models and relationships are defined in the canonical schema at `libs/runefoble_auth/schema/runefoble.zed`. The `SpiceDBClient` in `libs/runefoble_auth` connects over gRPC using the official `authzed` SDK. It does not fall back to an in-memory store. Unit tests use `MockSpiceDBClient` explicitly.

---

## 1. Defining Zanzibar Schema Rules

Schema definitions live in `libs/runefoble_auth/schema/runefoble.zed`.

### Schema Identifier Conventions
SpiceDB enforces that relation, permission, and definition names follow `^[a-z][a-z0-9_]{1,62}[a-z0-9]$` (minimum 3 characters). Avoid two-letter identifiers (e.g. use `game_master` or `dungeon_master`, not `gm` or `dm`).

Example:
```zed
definition campaign {
    relation owner: user
    relation dungeon_master: user
    relation game_master: user
    relation player: user
    relation spectator: user

    // Owner has supreme management permissions
    permission manage = owner

    // DMs, GMs, and Owner can run sessions, mutate world, assign penalties
    permission run_session = owner + dungeon_master + game_master

    // Active players can interact with their campaign assets
    permission play = run_session + player

    // Spectators can observe the live game
    permission view = play + spectator
}
```

### Name Contract
Every name in code must exist in `runefoble.zed`. Four kinds of name exist. Use each one for its own purpose:

| Kind | Example | Written as a tuple? | Checked with `check_permission`? |
|---|---|---|---|
| Type | `campaign` | No | No |
| Relation (a stored grant) | `game_master`, `player`, `spectator` | Yes | No |
| Permission (a computed check) | `run_session`, `play`, `view` | No | Yes |
| Role name (a label) | `gm`, `dm`, `read`, `control` | Never | Never |

Rules:
- Write only relations. `campaign#play` is not a relation, so SpiceDB rejects it.
- Check only permissions. `campaign#owner` is a relation, so it is not a permission.
- Map a domain action to its `(type, permission)` pair in `ACTION_PERMISSIONS` (`libs/runefoble_auth/src/runefoble_auth/contract.py`). Do not write the names inline.
- The Game Master relation is `game_master`. `gm` is not a relation.

### Name Contract Gate

`libs/runefoble_auth/tests/test_production_name_contract.py` parses every production module under `services/`, `gateway/`, and `libs/` with `ast`. It reads the literal type, permission, and relation names that the code passes to `check_permission`, `write_relationship`, `touch_relationship`, `delete_relationship`, and `require_zanzibar_permission`, and the `(type, permission)` pairs in `ACTION_PERMISSIONS`. It asserts that each name exists in `runefoble.zed` with the right kind. A write also checks that the relation accepts the subject type. The gate has no allowlist. A variable name is not checked. Add a new SpiceDB call with a literal name, and the gate checks it on the next run.

Run it with `uv run pytest -q libs/runefoble_auth/tests/test_production_name_contract.py`.

### Retired Definitions

The `session` definition is removed (TASK-0856). `game_session#campaign` is the one campaign link for a session. `campaign.tuples.link_session` writes it, and ADR-0015 (a) names it the authoritative link. Session actions (`session.control`, `session.participate`, `session.observe`) check `game_session`. A definition stays only while a check or a write uses it.

The schema change does not rewrite stored tuples. A deployment that holds `session#campaign` tuples must write `game_session#campaign` for each session. `POST /api/v1/campaigns/{campaign_id}/sessions/reconcile-links` does this for every session of one campaign, and it requires `run_session`. Bounty and negotiation tuples with a `session` subject are not rewritten by this route.

`runefoble_auth.contract` parses the schema once. `require_permission`, `require_relation`, and `require_subject_type` raise `SchemaContractError` for a name that the schema does not define. `SchemaContractError` is an `AuthzSchemaError`. The live client raises `AuthzSchemaError` for the same call.

### Validating Schema Changes
Validate schema syntax using the `zed` CLI or container:
```bash
docker run --rm -v $(pwd)/libs/runefoble_auth/schema/runefoble.zed:/schema.zed authzed/zed:latest validate /schema.zed
```

---

## 2. Bootstrapping and Schema Migrations

### Automated Helm Migration Job
During cluster deployment (`helm install` or `helm upgrade`), SpiceDB datastore schema and Zanzibar definitions are bootstrapped automatically:
- **Datastore Migrations**: An `initContainer` (`datastore-migrate` / `spicedb-migrate`) runs `spicedb datastore migrate head` against PostgreSQL prior to starting `spicedb serve` and before applying schema definitions.
- **Template**: `deployments/helm/runefoble/templates/spicedb-schema-job.yaml` and `deployments/helm/runefoble/templates/spicedb.yaml`
- **ConfigMap**: Mounts `runefoble.zed` from the chart files.
- **Job**: Executes `zed schema write /etc/spicedb/schema/runefoble.zed --endpoint spicedb:50051 --token <key> --insecure`.

### Python Migration CLI
You can also apply schema migrations programmatically or via CLI. Both read the preshared key from `RUNEFOBLE_SPICEDB_PRESHARED_KEY`. The key has no default. The commands below fail if the variable is unset.
The SpiceDB Service is `ClusterIP`. The Kind cluster does not map its gRPC port to the host.
Before you connect from the host, forward the port:
```bash
kubectl port-forward svc/spicedb 50051:50051
```
Keep the port-forward running in a separate terminal. `make dev` starts it for you when SpiceDB is unreachable.
```bash
# Using UV
export RUNEFOBLE_SPICEDB_PRESHARED_KEY=<operator-secret>
uv run python -m runefoble_auth.bootstrap_schema --endpoint localhost:50051

# Programmatic Python call (reads RUNEFOBLE_SPICEDB_PRESHARED_KEY)
from runefoble_auth.bootstrap_schema import bootstrap_schema

schema_text = await bootstrap_schema(endpoint="localhost:50051")
```

---

## 3. Connecting to SpiceDB

The `SpiceDBClient` connects directly to live SpiceDB over gRPC without silent mock fallbacks:

```python
from runefoble_auth.mock import MockSpiceDBClient
from runefoble_auth.spicedb import SpiceDBClient

# 1. Connect to live SpiceDB gRPC. The token comes from RUNEFOBLE_SPICEDB_PRESHARED_KEY.
client = SpiceDBClient(
    endpoint="spicedb:50051",
    insecure=True,
)

# 2. Offline / Unit Test Mock Mode (Explicit Mock)
mock_client = MockSpiceDBClient()
```

The preshared key is an operator secret. The library has no literal default. `SpiceDBClient` requires an explicit `endpoint` and `token`. `runefoble_auth.settings.SpiceDBSettings` holds the endpoint (`RUNEFOBLE_SPICEDB_ENDPOINT` or `SPICEDB_ENDPOINT`, default `localhost:50051`) and the key (`RUNEFOBLE_SPICEDB_PRESHARED_KEY`). `PlatformSettings` does not hold them. `load_spicedb_settings()` raises `ConfigurationError` when the key is unset or empty. A service that checks permissions calls it at startup, so it fails at startup without the key. A service that never checks permissions does not need the key. Tests set a throwaway value in the repository root `conftest.py`.

`SpiceDBClient` communicates strictly over gRPC. If the SpiceDB server is unreachable or fails, operations fail fast and raise exceptions rather than silently degrading to an in-memory mock, preventing permission desynchronization and data loss. For isolated unit tests, instantiate `MockSpiceDBClient` directly.

---

## 4. Writing and Deleting Relationships

### Writing Relationship Tuples
When an entity is created or a role is assigned, write the tuple to Zanzibar:
```python
# Grant player role on a campaign
await client.write_relationship(
    resource_type="campaign",
    resource_id="camp_101",
    relation="player",
    subject_type="user",
    subject_id="alice",
)

# Grant character ownership
await client.write_relationship(
    resource_type="character",
    resource_id="char_42",
    relation="owner",
    subject_type="user",
    subject_id="alice",
)

# Bind character to campaign
await client.write_relationship(
    resource_type="character",
    resource_id="char_42",
    relation="campaign",
    subject_type="campaign",
    subject_id="camp_101",
)
```

### Codex Privacy Relations
A codex entry has three privacy levels. Each level is one relation tuple:
```python
# Share a codex entry with the whole party (view for campaign play members)
await client.write_relationship(
    resource_type="codex_entry",
    resource_id="entry_7",
    relation="party_shared",
    subject_type="campaign",
    subject_id="camp_101",
)

# Make a codex entry visible to everyone who can view the campaign
await client.write_relationship(
    resource_type="codex_entry",
    resource_id="entry_7",
    relation="public",
    subject_type="campaign",
    subject_id="camp_101",
)
```
A private entry has no `party_shared` or `public` tuple. Only `author`, `editor`, and `reader` can view it.

### Deleting Relationship Tuples (Revocation)
When a role is revoked or an entity is removed:
```python
await client.delete_relationship(
    resource_type="campaign",
    resource_id="camp_101",
    relation="player",
    subject_type="user",
    subject_id="alice",
)

# Delete character owner relationship on deletion
await client.delete_relationship(
    resource_type="character",
    resource_id="char_42",
    relation="owner",
    subject_type="user",
    subject_id="alice",
)
```

---

## 5. Checking Object-Level Permissions

Always check fine-grained permissions against the resource rather than checking roles:

```python
# Check whether Alice can view the campaign session
can_view = await client.check_permission(
    resource_type="campaign",
    resource_id="camp_101",
    permission="view",
    subject_type="user",
    subject_id="alice",
)

if not can_view:
    raise HTTPException(status_code=403, detail="Forbidden")
```

### Use the Shared Subject Check

Routes do not write their own lookup. Use the two helpers in `runefoble_auth.permissions`:

- `check_subject(spicedb, resource_type, resource_id, permission, user_id)` returns `True` or `False`. Use it when the route decides between two outcomes.
- `require_subject(spicedb, resource_type, resource_id, permission, user_id, *, detail=None, denial=None)` raises `PermissionDenied`, an `HTTPException` with status `403`. The default detail names the subject, the permission, and the resource. Pass `detail` only when a route must keep its own wording. Pass `denial` only when a route must keep its own 403 body.

```python
from runefoble_auth.permissions import require_subject

await require_subject(spicedb, "campaign", campaign_id, "view", caller_id)
```

Both helpers pass the user subject to SpiceDB. Neither helper turns a SpiceDB failure into a denial. A failure raises `AuthzError`, and the handlers in the section below map it to `503`.

### Guard a Route by Path Resource
When a route names the resource in its path, use `require_permission` in a service. It builds a route dependency. The check runs before the handler, so a refused caller never reaches the handler body:

```python
from uuid import UUID

from fastapi import Depends
from runefoble_auth.permissions import require_permission

EDIT_CHARACTER = [
    Depends(
        require_permission(
            "character",
            "edit",
            "character_id",
            principal=get_principal,
            id_type=UUID,
        )
    )
]
```

- `principal` is the service identity dependency. It returns an object with a `user_id`.
- `id_param` is the path parameter name. `id_type` sets its type, so an invalid value answers `422`.
- Pass `allow_service=True` with the service identity dependency (`get_caller_or_service`) to let the service credential pass without a user. A call with no user and no service credential is denied.
- Pass `denial=` to keep a route-specific 403 body. The callable receives `(resource_type, resource_id, permission, user_id)` and returns the `HTTPException`.

The standard 403 detail, the `401` for a missing credential, and the `503` for a SpiceDB failure stay the same as for `require_subject`.

### HTTP Failure Mapping

Every service that checks SpiceDB calls `install_authz_error_handlers(app)` from `runefoble_auth.authz_http` once at start-up. Do not add a local handler or a copy of the mapping.

- Any `AuthzError` (SpiceDB unreachable, timed out, or a write not applied) returns `503` with `{"error": "authorization_unavailable"}`. A failed check is never a denial or an allow.
- An `AuthzSchemaError` (a name missing from `runefoble.zed`) returns `500` with `{"error": "authorization_schema_error", "error_id": "<uuid>"}`. The full error is in the log under that id.

Let the `AuthzError` propagate from the helper. Do not turn it into an `HTTPException` with another body.

### Listing Resources a Subject Can Access
To list the resources of one type that a subject can use, call `lookup_resources`. The check runs in SpiceDB, so the result follows the schema. Do not read every tuple and filter in code:

```python
campaign_ids = await client.lookup_resources(
    resource_type="campaign",
    permission="view",
    subject_type="user",
    subject_id="alice",
)
```

The mock client returns only resources that hold at least one direct tuple. The live client returns every resource that the schema grants. `game_session` uses this call for `GET /api/v1/campaigns`. It sends one call for each permission that the response needs, and it does not send a `check` for each campaign (TASK-0907). Use this pattern for any list that shows per-item permissions.

### FastAPI Dependency Factory
A gateway composite route (one that combines several owner reads) checks its permission with `require_zanzibar_permission`:
```python
from fastapi import APIRouter, Depends
from gateway_api.auth import require_zanzibar_permission

router = APIRouter()


@router.get(
    "/api/v1/spectate/{session_id}",
    dependencies=[
        Depends(
            require_zanzibar_permission(
                "observe", resource_type="game_session", resource_param="session_id"
            )
        )
    ],
)
async def get_spectator_state(session_id: str):
    return {"status": "active"}
```

A gateway proxy route does not check. It verifies the token and forwards it. The owning service checks the permission in its own dependency. See [Call Owning Services Through the Gateway](call-owning-services-through-the-gateway.md#permission-rule).

Service routes check with `require_permission` or `require_subject` in their own bounded context, for example `character_sheet` in `services/character_sheet/src/character_sheet/dependencies.py`.
```

---

### Character Delete Check
Only the character owner holds the `delete` permission. The DM can edit a character but cannot delete it:
```python
can_delete = await client.check_permission(
    resource_type="character",
    resource_id="char_42",
    permission="delete",
    subject_type="user",
    subject_id="alice",
)
```
Do not check `owner` as a permission. `owner` is a relation, not a permission.

---

## 6. Testing with In-Memory SpiceDB Test Server

To test live gRPC against SpiceDB without running PostgreSQL:
```bash
docker run -d --rm -p 50051:50051 authzed/spicedb:v1.34.0 serve-testing
```
The `serve-testing` mode provides an in-memory, fully-isolated Zanzibar engine where every client-supplied token isolates its own graph.

### Live Authorization Suite
Run the live name-contract suite with:
```bash
make test-authz-live
```
The target sets `RUNEFOBLE_REQUIRE_LIVE_SPICEDB=1` and runs `uv run pytest -m authz_live`. The suite needs a reachable Docker daemon. With the flag set, a missing Docker or a failed container start raises an error. It does not skip. Without the flag, the same tests skip when Docker is missing. `make test` keeps its default behaviour.

The `live_spicedb_with_schema` fixture (module scope, in `tests/helpers/spicedb.py`):
- Starts `serve-testing` with the image tag from `deployments/helm/runefoble/values.yaml` (`spicedb.image`).
- Loads `runefoble.zed` through `bootstrap_schema`. A failed write fails the fixture.
- Yields the endpoint and a `SpiceDBClient`.

Container lifetime (`tests/helpers/container_owner.py`):
- Each test container carries the pid and host name of the pytest process that started it (`runefoble.test.owner-pid`, `runefoble.test.owner-host`).
- Before a fixture starts a container, it removes the labelled containers whose owner process is dead on this host. A killed run skips teardown, so its container is removed by the next run.
- Containers of a live owner, and containers without these labels, are never removed.
- The PostgreSQL test fixture (`postgres_service` in `tests/helpers/postgres.py`) follows the same rule.

`tests/test_authz_live_contract.py` runs against this fixture. It checks that a permission name written as a relation is rejected, that `game_master` grants `run_session`, and that an undefined permission check raises `AuthzSchemaError`.

Tests that need the shared client use `tests/helpers/spicedb_factory.py`. The autouse fixture `default_spicedb_client` in `tests/helpers/service_harness.py` swaps the factory client for a fresh strict mock on every test. A test that needs live SpiceDB requests `live_spicedb_with_schema` instead.
