# How-To: Call Owning Services Through the Gateway

Use this guide to add a gateway route that calls an owning bounded context. The route uses the shared service client. See the [Service Client reference](../reference/service-client.md) for the full contract.

## Before you start

- The gateway holds no domain state. The owning service holds the state and checks the token.
- The gateway verifies the caller's bearer token in the route dependencies. A proxy route does not check object permissions. Its owner checks them. See [Permission rule](#permission-rule).
- A failed upstream call returns an error. Do not return a canned or cached value.

## Permission rule

Every gateway route follows one rule (TASK-0845):

- A **proxy route** verifies the bearer token and forwards it to the owner. The owner checks the object permission. The gateway adds no check. A stranger gets the owner's `403`, and the gateway passes it through unchanged.
- A **composite route** builds its reply from several owner reads, so no single owner sees the whole reply. The gateway checks the permission that the reply needs, with `require_zanzibar_permission`.

A proxy route keeps a gateway check only when the owner does not check the same permission for the same resource. These routes keep one:

| Route | Gateway check | Why the check stays |
|---|---|---|
| `GET /api/v1/spectate/{session_id}` (composite) | `observe` on the session | Composite. It combines the session and board reads. |
| `GET /overlay/party-vitals/{session_id}` (composite) | `observe` on the session | Composite. It combines the session and board reads. |
| `POST /api/v1/sessions/{session_id}/hot-swap` | `observe` on the session | The owner checks `participate` and `character.edit`. The permissions differ. |
| `POST /api/v1/sessions/{session_id}/dm-override` | `control` on the session | Open owner gap. `game_session` checks only the token. Remove this check when the owner checks `control`. |
| `POST /api/v1/sessions/{session_id}/atmosphere` | `control` on the session | Open owner gap. `game_session` checks only the token. Remove this check when the owner checks `control`. |
| `GET /api/v1/sessions/{session_id}/events` | `observe` on the session | The owner answers `404` for an unknown session before it checks `observe`. Without the gateway check, a stranger could learn whether a session exists. |
| `GET /api/v1/sessions/{session_id}/absentee-recap` | `observe` on the session | Same reason as `events`. |

WebSocket sockets are not proxy routes. The gateway checks `session.observe` at admission, and it checks `session.participate` before it relays each inbound frame.

To add a proxy route, add the owner check. Then test that a stranger gets the owner's `403` through the gateway. Do not add a gateway check to the route.

## 1. Set the base URL

If the owning service has no field yet, add one to `PlatformSettings` in `libs/runefoble_platform/src/runefoble_platform/config.py`. Use the `RUNEFOBLE_<SERVICE>_URL` name, with `default=None`.

Then add the service to `OWNER_URL_FIELDS` in `libs/runefoble_platform/src/runefoble_platform/service_client/owners.py`. Both gateways read this map:

```python
OWNER_URL_FIELDS = {
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
from gateway_api.auth import get_principal
from gateway_api.proxy import forward_json


@router.get(
    "/api/v1/campaigns/{campaign_id}/atlas",
    dependencies=[Depends(get_principal)],
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
- Do not call `require_zanzibar_permission` on a proxy route. The owner checks the permission. Use it only on a composite route (see [Permission rule](#permission-rule)).
- Do not read `os.environ` for a service URL. The registry holds the URL.
- Do not add an `except` block that returns local data. The handlers in `upstream_errors.py` map each failure.
- Do not copy client headers to the upstream request. Only the bearer token, the service credential, and the trace context leave the gateway.
- Do not import a service package in `gateway_api`. Forward the body instead. Use `forward_bytes` when the owner validates the body. `forward_bytes` sends the caller's raw body and its `Content-Type` unchanged, so a malformed body returns the owner's `422`, and it relays the owner's reply unchanged. Use `forward_json` only when the gateway builds the JSON itself.
- The import-contract gate (`make lint`, `uv run lint-imports`) fails when `gateway_api` imports a service package, directly or through a library. The contract is `gateway_api must not import a service package` in the root `pyproject.toml`. Keep the service list in that contract in step with `services/`.

### A pass-through route as a table row

If the route only forwards the request, add a `ProxyRoute` row to the module's `ROUTES` tuple instead of a handler. Each field is documented in `gateway_api/proxy_table.py`:

```python
ProxyRoute(
    "GET",
    "/api/v1/campaigns/{campaign_id}/atlas",
    ("api", "v1", "campaigns", "{campaign_id}", "atlas"),
    "campaign_lore",
    name="get_campaign_atlas",
    doc="Read the campaign atlas from campaign_lore.",
    principal=True,
)
```

Then call `register_proxy_routes(router, ROUTES)` once at the end of the module. Use a row for each route that needs no check and no transform. Keep a hand-written handler for a composite route, a body transform, a typed reply, or a second owner call. Add an owner route function to `runefoble_platform.service_client.owner_routes` for each owner route that the MCP gateway calls, or that a gateway module builds by path. A row names that function in `owner=` and does not repeat the owner path in `owner_segments`. Use `owner_segments` only when no such function exists:

```python
ProxyRoute(
    "GET",
    "/api/v1/compendium/monsters/{name}",
    (),
    "rules_compendium",
    name="get_monster",
    doc="Monster stat block by name.",
    owner=owner_routes.get_monster,
    principal=True,
)
```

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

Add the handler to the `router` in `gateway_api/routers/realtime.py`. The composition root (`gateway_api/main.py`) includes that router once. It defines no socket handler itself.

```python
@router.websocket("/ws/minigames/{table_id}")
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

## Relay a campaign socket action to an owner

The campaign socket (`/ws/campaigns/{id}`) does not relay frames. It relays each action as one owner call. Add an action in two steps:

1. Add one builder to `ACTIONS` in `gateway_api/campaign_actions.py`. The builder returns the owner route from `owner_routes` and the body. It copies only the fields the owner needs. Add the owner route function to `runefoble_platform.service_client.owner_routes` first.
2. Add the owner check and the owner event in the owning service. The gateway adds no permission check and publishes no event.

`send_owner_call` in `gateway_api/campaign_owner_call.py` sends the call with the caller's token. It maps the owner answer to a frame. The reference table is in [Campaign socket actions](../reference/ports-and-endpoints.md#campaign-socket-actions-task-0883).

Test the action through the socket with a live owner (`game_session_upstream`, `board_state_upstream`, `character_sheet_upstream`), as `gateway/api/tests/test_blackbox_gateway_campaign_socket.py` does.

## Checklist

- [ ] Setting field exists, with `default=None` and no `localhost` default.
- [ ] Service name is in `OWNER_URL_FIELDS` (`runefoble_platform.service_client.owners`).
- [ ] Helm renders the variable for `gateway-api`.
- [ ] Route calls `forward_json(..., service=..., ...)` with a timeout.
- [ ] Tests set the variable before they enter `TestClient`, and cover the 5 cases above.
- [ ] A relayed socket sends the bearer subprotocol upstream, forwards frames both ways, and passes owner close codes.
