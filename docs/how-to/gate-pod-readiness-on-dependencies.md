# Gate Pod Readiness on Dependencies

This guide tells you how to make a service report ready only after its dependencies answer. Use it for a service whose write routes need the event store, SpiceDB or Redis.

## Why

Kubernetes sends traffic to a pod when its readiness probe passes. Without a probe, a pod is Ready when its container starts. The first request then opens the event store pool, runs the event store schema check, and opens the SpiceDB gRPC channel. If one of these fails, a player gets `503` (TASK-0929).

`runefoble_platform.readiness` moves that first contact into the probe:

- `ReadinessGate` holds one probe for each dependency.
- `GET /readyz` runs the probes that have not answered yet. The probes run at the same time. Each probe has a time limit of 2.5 seconds.
- A probe that answers is not run again. After start-up, `/readyz` makes no calls.
- A failed probe is logged at warning level (`Readiness probe <name> failed: <error>`). `/readyz` then answers `503` with the failures.
- `/healthz` does not change. It stays the cheap liveness check.

## 1. Write the probes

Write one probe for each dependency. Each probe makes one cheap call through the same client that the routes use. Put the probes in the service package, next to `main.py`.

```python
from uuid import UUID

from fastapi import FastAPI
from runefoble_auth.factory import get_spicedb_client
from runefoble_platform.event_sourcing import get_event_store
from runefoble_platform.readiness import ReadinessGate


def build_readiness_gate(app: FastAPI) -> ReadinessGate:
    async def event_store() -> None:
        await get_event_store().event_exists(UUID(int=0))

    async def spicedb() -> None:
        await get_spicedb_client().read_schema()

    async def redis() -> None:
        client = await app.state.container.event_bus.get().get_client()
        await client.ping()

    return ReadinessGate({"event_store": event_store, "spicedb": spicedb, "redis": redis})
```

Do not read a client at import time. Read it inside the probe. Then a test that replaces a client through its public seam also replaces the client that the probe uses.

The reference implementation is `services/game_session/src/game_session/readiness.py`.

## 2. Add the route

Call `add_readiness_route` in `create_app`, after `/healthz`:

```python
from runefoble_platform.readiness import add_readiness_route

app.add_api_route("/healthz", health_check, methods=["GET"])
add_readiness_route(app, "game_session", build_readiness_gate(app))
```

The route is public, as `/healthz` is. Add `/readyz` to the public path list of the service identity test (`tests/test_blackbox_service_identity.py`).

## 3. Point the Helm probe at the route

Set the probe paths of the service in `deployments/helm/runefoble/values.yaml`:

```yaml
gameSession:
  readinessPath: /readyz
  readinessTimeoutSeconds: 3
  livenessPath: /healthz
```

`readinessTimeoutSeconds` must be longer than the probe time limit of 2.5 seconds. The default is 1 second. Run `make helm-lint` and `make helm-template`.

## 4. Test through the frontdoor

Test the gate with a dependency that is not up yet. `tests/helpers/tcp_relay.py` binds a loopback port but does not listen, so a client gets "connection refused". `relay.come_up()` starts to forward to the real dependency. The test changes only the network.

1. Point the client at the relay port.
2. Call `GET /readyz`. Expect `503` and the dependency name in `pending`.
3. Call a write route. Expect `503` and a log line that names the failure.
4. Call `relay.come_up()`. Poll `GET /readyz` until it answers `200`.
5. Call the write route again. Expect success.

The reference test is `tests/test_blackbox_game_session_readiness.py`.

## Related

- [Run supervised Redis Stream consumers](run-supervised-redis-stream-consumers.md): consumer status on `/healthz`.
- [Ports and endpoints](../reference/ports-and-endpoints.md): the `/readyz` route of `game-session`.
- ADR-0005 (Kind and Helm) and ADR-0015 (failures are visible).
