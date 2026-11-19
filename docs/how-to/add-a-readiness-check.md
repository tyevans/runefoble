# Add a Readiness Check to a Service

This guide tells you how to make a service report ready only after its dependencies answer. Every app service must do this (TASK-0930). Each service registers only the dependencies that it uses.

## Why

Kubernetes sends traffic to a pod when its readiness probe passes. A pod that is Ready before its dependencies answer gets requests that fail. The first request opens the event store pool, runs the event store schema check, and opens the SpiceDB gRPC channel. If one of these fails, a player gets `503` (TASK-0929).

`runefoble_platform.readiness` moves that first contact into the probe:

- `ReadinessGate` holds one check for each dependency.
- `GET /readyz` runs the checks that have not answered yet. The checks run at the same time. Each check has a time limit of 2.5 seconds.
- A check that answers is not run again. After start-up, `/readyz` makes no calls.
- A failed check is logged at warning level (`Readiness probe <name> failed: <error>`). `/readyz` then answers `503` with `status: not_ready` and `pending` (dependency name to error).
- `/healthz` does not change. It stays the cheap liveness check.

## The shared checks

| Check | Module | What it calls |
|---|---|---|
| `event_store_probe()` | `runefoble_platform.readiness` | `event_exists` on `get_event_store()`. The first call opens the pool and runs the schema check. |
| `redis_probe(get_bus)` | `runefoble_platform.readiness` | `PING` on the bus that `get_bus()` returns. |
| `spicedb_probe()` | `runefoble_auth.readiness` | `read_schema` on `get_spicedb_client()`. The first call opens the gRPC channel. |

Each check reads its client when it runs, not at import time. Then a test that replaces a client through its public seam also replaces the client that the check uses.

For a dependency that has no shared check (for example Silo or an owning service), write an `async def` with no arguments that makes one cheap call and raises on failure. Do not add the owning services of a gateway: one owner that is down must not take the gateway out of service.

## 1. Add the route

Call `add_readiness_route` where the service adds `/healthz`. The first argument is the app or the router that holds `/healthz`:

```python
from runefoble_platform.readiness import add_readiness_route

app.add_api_route("/healthz", health_check, methods=["GET"])
add_readiness_route(app, "game_session")
```

The route is public, as `/healthz` is. `tests/test_blackbox_service_identity.py` lists `/readyz` as a public path.

## 2. Set the gate in the lifespan

Build the gate at the start of the lifespan, and give it to the app with `set_readiness_gate`. A new lifespan gets a new gate, so no dependency counts as answered before the app starts.

```python
from runefoble_auth.readiness import spicedb_probe
from runefoble_platform.readiness import (
    ReadinessGate,
    event_store_probe,
    redis_probe,
    set_readiness_gate,
)


async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    container = build()
    app.state.container = container
    readiness = {
        "event_store": event_store_probe(),
        "spicedb": spicedb_probe(),
        "redis": redis_probe(container.event_bus.get),
    }
    set_readiness_gate(app, ReadinessGate(readiness))
    ...
```

The reference implementations are `services/game_session/src/game_session/main.py` (event store, SpiceDB, Redis) and `gateway/api/src/gateway_api/routers/health.py` (SpiceDB, Redis).

## 3. Use the default Helm probe

The shared template helper `runefoble.probes` (`deployments/helm/runefoble/templates/_helpers.tpl`) gives every app container an HTTP readiness probe. Its values in `deployments/helm/runefoble/values.yaml` are:

| Key | Default | Meaning |
|---|---|---|
| `readinessPath` | `/readyz` | Readiness probe path on the service port. |
| `readinessTimeoutSeconds` | `3` | Time limit of one probe call. It must be longer than the 2.5 second check limit. |
| `livenessPath` | not set | Liveness probe path. No liveness probe when it is not set. |

A service that has no `/readyz` yet sets `readinessPath: /healthz`. When you add `/readyz` to the service, remove that line so that the default applies. Then run `make helm-lint` and `make helm-template`, and add the service to `GATED` in `tests/test_blackbox_helm_readiness_probes.py`.

## 4. Test through the frontdoor

Test the gate with a dependency that is not up yet. `tests/helpers/tcp_relay.py` binds a loopback port but does not listen, so a client gets "connection refused". `relay.come_up()` starts to forward to the real dependency. The test changes only the network.

1. Point the client at the relay port through its public seam (for example `shared_spicedb_client` or `set_event_store`).
2. Call `GET /readyz`. Expect `503` and the dependency name in `pending`.
3. If the service has a write route that needs the dependency, call it. Expect `503` and a log line that names the failure.
4. Call `relay.come_up()`. Poll `GET /readyz` until it answers `200`.

The reference tests are `tests/test_blackbox_game_session_readiness.py` and `tests/test_blackbox_gateway_readiness.py`.

## Related

- [Run supervised Redis Stream consumers](run-supervised-redis-stream-consumers.md): consumer status on `/healthz`.
- [Ports and endpoints](../reference/ports-and-endpoints.md): the `/readyz` routes.
- ADR-0005 (Kind and Helm) and ADR-0015 (failures are visible).
