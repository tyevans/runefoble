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
from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient

# 1. Connect to live SpiceDB gRPC. The token comes from RUNEFOBLE_SPICEDB_PRESHARED_KEY.
client = SpiceDBClient(
    endpoint="spicedb:50051",
    insecure=True,
)

# 2. Offline / Unit Test Mock Mode (Explicit Mock)
mock_client = MockSpiceDBClient()
```

The preshared key is an operator secret. The library has no literal default. If `RUNEFOBLE_SPICEDB_PRESHARED_KEY` is unset and no `token` is passed, the constructor raises `RuntimeError`. Services read the same setting through `PlatformSettings.spicedb_preshared_key` and fail at startup when it is unset. Tests set a throwaway value in `tests/conftest.py`.

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

The mock client returns only resources that hold at least one direct tuple. The live client returns every resource that the schema grants. `game_session` uses this call for `GET /api/v1/campaigns`.

### FastAPI Dependency Factory
In HTTP routes, use `require_zanzibar_permission`:
```python
from fastapi import APIRouter, Depends
from gateway_api.auth import require_zanzibar_permission

router = APIRouter()


@router.get(
    "/api/v1/sessions/{session_id}",
    dependencies=[Depends(require_zanzibar_permission("view", resource_type="campaign"))],
)
async def get_session(session_id: str):
    return {"status": "active"}


@router.get(
    "/api/v1/characters/{character_id}",
    dependencies=[
        Depends(
            require_zanzibar_permission(
                "view", resource_type="character", resource_param="character_id"
            )
        )
    ],
)
async def get_character(character_id: str):
    return {"id": character_id}
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

`tests/test_authz_live_contract.py` runs against this fixture. It checks that a permission name written as a relation is rejected, that `game_master` grants `run_session`, and that an undefined permission check raises `AuthzSchemaError`.

Tests that need the shared client use `tests/helpers/spicedb_factory.py`. The root `tests/conftest.py` autouse fixture swaps the factory client for a fresh strict mock on every test. A test that needs live SpiceDB requests `live_spicedb_with_schema` instead.

### Automated Test Suites & Fixtures
Automated testing uses the `live_spicedb_endpoint` fixture defined in `tests/helpers/spicedb.py` and registered globally via `tests/conftest.py`:
- **`tests/test_spicedb_schema_bootstrap.py`**: Fast-running unit suite validating `runefoble.zed` existence, definition syntax, error handling for empty schemas, and graceful offline fallback behavior when endpoints are unreachable.
- **`tests/test_blackbox_spicedb_live_grpc.py`**: Integration blackbox suite evaluating live Zanzibar graph permissions, frontdoor role assignment (`POST /api/v1/campaigns/{id}/roles`), and immediate permission revocation upon relationship tuple deletion.
- **`tests/test_websocket_zanzibar_connect_auth.py`**: Verifies handshake authentication, campaign viewer/reader authorization, 4403 rejection for unauthorized subjects, and dynamic permission revocation disconnecting active sessions.
- **`tests/test_websocket_zanzibar_mutators.py`**: Verifies fine-grained Zanzibar object-level permissions on token movement, DM-only monster spawning/scenes, character sheet mutations, Redis stream publishing, and mid-session relation revocations.
- **`tests/test_blackbox_spicedb_auth_sync.py`**: Blackbox frontdoor suite testing Zitadel-to-SpiceDB relationship synchronization, claim translations, and domain event dispatch.
- **`tests/test_blackbox_spicedb_live.py`**: Blackbox frontdoor suite evaluating `SpiceDBClient` operations and fallback handling.

---

## 7. Modular Mock SpiceDB Engine Architecture

For lightweight unit and offline testing, `runefoble_auth` provides an in-memory mock engine decomposed into single-responsibility submodules under `runefoble_auth.mock`:
- **`runefoble_auth.schema_graph`**: Parses Zed schema definitions into `SchemaGraph`, extracting relations, permissions, and target types. It is shared by the name contract and the mock.
- **`runefoble_auth.mock.evaluator`**: Recursively evaluates schema-defined permissions, union rules, and arrow expressions (`relation->permission`). It holds no role-name grants and no alias table. Caveats are supported.
- **`runefoble_auth.mock.client`**: Provides `MockSpiceDBClient` tuple storage, relationship CRUD, touch updates, and permission checks. It enforces the name contract. A write to an undefined type, relation, or subject raises `SchemaContractError`. A check of an undefined permission raises it too.
- **`runefoble_auth.mock_spicedb`**: Defect (DoR 9): facade module re-exporting `MockSpiceDBClient` and `Relationship`. Removal: TASK-0486.


