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

The gateway reads its base URLs at start-up. Add the variable to the `gateway-api` consumer list in `deployments/helm/runefoble/templates/services.yaml`. Use the in-cluster address of the service. Do not use `localhost`.

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

## 4. Test the route through public frontdoors

Use a stand-in owning service on a loopback port. Use `serve(...)` from `tests/helpers/live_services.py`. Set the variable before the gateway starts. The gateway reads settings in its lifespan, so enter the `TestClient` context after you set the variable:

```python
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app

from tests.helpers.live_services import serve


def test_atlas_forwards_bearer_token(monkeypatch, signing_issuer):
    with serve(stand_in_lore) as lore_url:
        monkeypatch.setenv("CAMPAIGN_LORE_URL", lore_url)
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

## Checklist

- [ ] Setting field exists, with `default=None` and no `localhost` default.
- [ ] Service name is in `UPSTREAM_SETTINGS`.
- [ ] Helm renders the variable for `gateway-api`.
- [ ] Route calls `forward_json(..., service=..., ...)` with a timeout.
- [ ] Tests set the variable before they enter `TestClient`, and cover the 5 cases above.
