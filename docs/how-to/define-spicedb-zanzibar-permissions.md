# How-To: Define and Check SpiceDB Zanzibar Permissions

## Overview
Runefoble enforces fine-grained, object-level authorization across campaigns, game sessions, characters, and tactical boards using **SpiceDB** (a Google Zanzibar-inspired graph permission system).

All permission models and relationships are defined in the canonical schema at `libs/runefoble_auth/schema/runefoble.zed`. The `SpiceDBClient` in `libs/runefoble_auth` connects over gRPC using the official `authzed` SDK while automatically falling back to an in-memory mock store for offline unit tests.

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
You can also apply schema migrations programmatically or via CLI:
```bash
# Using UV
uv run python -m runefoble_auth.bootstrap_schema --endpoint localhost:50051 --token runefoble_secret_key

# Programmatic Python call
from runefoble_auth.bootstrap_schema import bootstrap_schema

schema_text = await bootstrap_schema(endpoint="localhost:50051", token="runefoble_secret_key")
```

---

## 3. Connecting to SpiceDB

The `SpiceDBClient` seamlessly handles live gRPC and disconnected test modes:

```python
from runefoble_auth.spicedb import SpiceDBClient

# 1. Connect to live SpiceDB gRPC
client = SpiceDBClient(
    endpoint="spicedb:50051",
    token="runefoble_secret_key",
    insecure=True,
)

# 2. Offline / Unit Test Mock Mode
mock_client = SpiceDBClient(use_mock=True)
```

If `use_mock=False` but the gRPC server is unreachable, `SpiceDBClient` logs a warning and automatically falls back to in-memory evaluation so tests and services degrade gracefully.

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

# Bind character to campaign
await client.write_relationship(
    resource_type="character",
    resource_id="char_42",
    relation="campaign",
    subject_type="campaign",
    subject_id="camp_101",
)
```

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
```

---

## 6. Testing with In-Memory SpiceDB Test Server

To test live gRPC against SpiceDB without running PostgreSQL:
```bash
docker run -d --rm -p 50051:50051 authzed/spicedb:v1.34.0 serve-testing
```
The `serve-testing` mode provides an in-memory, fully-isolated Zanzibar engine where every client-supplied token isolates its own graph.

### Automated Test Suites & Fixtures
Automated testing uses the `live_spicedb_endpoint` fixture defined in `tests/helpers/spicedb.py` and registered globally via `tests/conftest.py`:
- **`tests/test_spicedb_schema_bootstrap.py`**: Fast-running unit suite validating `runefoble.zed` existence, definition syntax, error handling for empty schemas, and graceful offline fallback behavior when endpoints are unreachable.
- **`tests/test_blackbox_spicedb_live_grpc.py`**: Integration blackbox suite evaluating live Zanzibar graph permissions, frontdoor role assignment (`POST /api/v1/campaigns/{id}/roles`), and immediate permission revocation upon relationship tuple deletion.
