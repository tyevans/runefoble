# How-To: Call Owning Services Through the Gateway

Use this guide to add a gateway route that calls an owning bounded context. The route uses the shared service client. See the [Service Client reference](../reference/service-client.md) for the full contract.

## Before you start

- The gateway holds no domain state. The owning service holds the state and checks the token.
- The gateway verifies the caller's bearer token in the route dependencies. Use `require_zanzibar_permission` for object checks.
- A failed upstream call returns an error. Do not return a canned or cached value.

## 1. Set the base URL

If the owning service has no field yet, add one to `PlatformSettings` in `libs/runefoble_platform/src/runefoble_platform/config.py`. Use the `RUNEFOBLE_<SERVICE>_URL` name, with `default=None`.

Then add the service to `UPSTREAM_SETTINGS` in `gateway/api/src/gateway_api/upstreams.py`:

```python
UPSTREAM_SETTINGS = {
    ...
    "rules_compendium": "rules_compendium_url",
}
```

The key is the service name. It appears in logs and in the error body.

## 2. Render the variable in Helm

The gateway reads its base URLs at start-up. Set `urlEnv` on the owning service's entry under `services` in `deployments/helm/runefoble/values.yaml`, and add `gateway-api` to that entry's `consumers` list. Use the in-cluster address of the service. Do not use `localhost`.

Run `make helm-lint` and `make helm-template`.

## 3. Write the route

Call `forward_json` from `gateway_api.proxy`. Pass the service name, the method, and the path:

```python
from gateway_api.proxy import forward_json


@router.get(
    "/api/v1/campaigns/{campaign_id}/atlas",
    dependencies=[Depends(require_zanzibar_permission("view", "campaign", "campaign_id"))],
)
async def get_campaign_atlas(campaign_id: str, request: Request) -> Any:
    return await forward_json(
        request,
        service="campaign_lore",
        method="GET",
        path=f"/api/v1/campaigns/{campaign_id}/atlas",
        timeout=5.0,
    )
```

Rules:

- Set `timeout` for each route. The default is 5.0 seconds.
- Do not read `os.environ` for a service URL. The registry holds the URL.
- Do not add an `except` block that returns local data. The handlers in `upstream_errors.py` map each failure.
- Do not copy client headers to the upstream request. Only the bearer token, the service credential, and the trace context leave the gateway.
- Do not import a service package in `gateway_api`. Forward the body instead. Use `forward_bytes` when the owner validates the body. `forward_bytes` sends the caller's raw body and its `Content-Type` unchanged, so a malformed body returns the owner's `422`, and it relays the owner's reply unchanged. Use `forward_json` only when the gateway builds the JSON itself.
- The import-contract gate (`make lint`, `uv run lint-imports`) fails when `gateway_api` imports a service package, directly or through a library. The contract is `gateway_api must not import a service package` in the root `pyproject.toml`. Keep the service list in that contract in step with `services/`.

## 4. Test the route through public frontdoors

Use a stand-in owning service on a loopback port. Use `serve(...)` from `tests/helpers/live_services.py`. Set the variable before the gateway starts. The gateway reads settings in its lifespan, so enter the `TestClient` context after you set the variable:

```python
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app

from tests.helpers.live_services import serve


def test_atlas_forwards_bearer_token(monkeypatch, signing_issuer):
    with serve(stand_in_lore) as lore_url:
        monkeypatch.setenv("RUNEFOBLE_CAMPAIGN_LORE_URL", lore_url)
        with TestClient(gateway_app) as client:
            res = client.get(f"/api/v1/campaigns/{campaign_id}/atlas", headers=headers)
    assert res.status_code == 200
```

Cover these cases:

| Case | Expected gateway result |
|---|---|
| Upstream 200 | 200 with the upstream body |
| Upstream 4xx | Same status and body |
| Upstream 5xx | 502 with `upstream` |
| Connection refused (`closed_port_url()`) | 503 with `upstream` |
| URL variable set to an empty string | 503 with `upstream` |

Run the targeted tests with `uv run pytest <file>`.

## Relay a WebSocket to an owner

Use `relay_websocket` from `gateway_api.websocket_relay` when the owner serves a socket. The gateway does not parse the frames. It does this, in order:

1. Checks the bearer subprotocol with the gateway verifier. A missing or invalid token closes with `1008` before accept.
2. Opens an upstream socket to the owner at the same path, with the same offered subprotocols. The owner gets the bearer. The gateway adds only the service credential and the trace headers.
3. Accepts the client with the subprotocol that the owner chose, then relays text and binary frames both ways.
4. Passes a close from either side to the other side with the same code and reason.

```python
@app.websocket("/ws/minigames/{table_id}")
async def gateway_standalone_minigame_ws(websocket: WebSocket, table_id: str) -> None:
    await relay_websocket(websocket, service="game_session", segments=("ws", "minigames", table_id))
```

Map the failures this way:

| Case | Client sees |
|---|---|
| Gateway token check fails | `1008`, before accept |
| Owner refuses the handshake with HTTP 401 | `1008` after accept |
| Owner refuses the handshake with HTTP 403 (authorization) | `4403` after accept |
| Owner unreachable, or slow to open | `1013` after accept |

A close code cannot be sent before accept, so the gateway accepts first and then closes with the code. The owner verifies the bearer again. The relay adds no permission check of its own.

Test a relayed socket with a stand-in owner from `serve(...)`. Check that the bearer subprotocol arrives, that text and binary frames round-trip, and that an owner close code reaches the client.

## Checklist

- [ ] Setting field exists, with `default=None` and no `localhost` default.
- [ ] Service name is in `UPSTREAM_SETTINGS`.
- [ ] Helm renders the variable for `gateway-api`.
- [ ] Route calls `forward_json(..., service=..., ...)` with a timeout.
- [ ] Tests set the variable before they enter `TestClient`, and cover the 5 cases above.
- [ ] A relayed socket sends the bearer subprotocol upstream, forwards frames both ways, and passes owner close codes.
