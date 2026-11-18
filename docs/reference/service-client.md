# Reference: Service Client

The shared typed HTTP client for calls from a gateway to an owning bounded context. It lives in `libs/runefoble_platform/src/runefoble_platform/service_client/`.

The gateway uses this client for every proxy call. Each proxy call goes through `gateway_api.proxy.forward_json`, which uses the registry in `gateway_api.upstreams`.

## Modules

| Module | Contents |
|---|---|
| `client.py` | `ServiceClient`, `UpstreamReply` |
| `errors.py` | `UpstreamError`, `UpstreamUnavailableError`, `UpstreamFailureError` |
| `headers.py` | `build_upstream_headers` |
| `paths.py` | `path` |

The package exports `ServiceClient`, `UpstreamReply`, `UpstreamError`, `UpstreamUnavailableError`, `UpstreamFailureError`, and `path`.

## `ServiceClient`

```python
ServiceClient(service: str, base_url: str, service_credential: str, transport: httpx.AsyncBaseTransport | None = None)
```

| Argument | Meaning |
|---|---|
| `service` | Service name. It appears in errors and in the gateway error body (`upstream`). |
| `base_url` | Base URL of the owning service. A trailing `/` is removed. |
| `service_credential` | Service credential (ADR-0015 e). It is sent on every call in the `X-Runefoble-Service-Credential` header. The constructor raises `ValueError` when it is blank. |
| `transport` | Optional HTTP transport. Tests pass a transport here. Production code omits it. |

Each instance owns one `httpx.AsyncClient`. Call `await aclose()` when the instance is no longer needed.

### `send`

```python
await client.send(
    method: str,
    path: str,
    *,
    authorization: str | None,
    timeout_s: float,
    json: Any = None,
    params: dict[str, str] | None = None,
) -> UpstreamReply
```

| Argument | Meaning |
|---|---|
| `method` | HTTP method, for example `GET` or `POST`. |
| `path` | Path that is appended to `base_url`, for example `/api/v1/soundscape/cue`. Build it with `path(...)` when a segment comes from input. |
| `authorization` | The verified `Authorization` header value of the caller, or `None`. |
| `timeout_s` | Timeout for this call, in seconds. It applies to connect, read, write, and pool. |
| `json` | Optional JSON body. |
| `params` | Optional query string values. |

The caller sets `timeout_s` for each call. The client sets no default timeout. The client does not retry. The client does not cache.

## `UpstreamReply`

A frozen dataclass. It holds an upstream 2xx or 4xx answer without change.

| Field | Type | Meaning |
|---|---|---|
| `status_code` | `int` | Status code from the owning service. |
| `content_type` | `str` | `content-type` header from the owning service. Defaults to `application/json`. |
| `body` | `bytes` | Raw response body. |

## Errors

| Error | Raised when | Attributes |
|---|---|---|
| `UpstreamUnavailableError` | A connect failure, a timeout, or no base URL is configured. | `service`, `reason` |
| `UpstreamFailureError` | The owning service answers with HTTP 5xx. | `service`, `status_code`, `body` |

Both errors inherit from `UpstreamError`, which carries `service`.

An upstream 2xx or 4xx answer is never an error at this level. `send` returns it as an `UpstreamReply`.

## Outgoing headers

`build_upstream_headers(authorization, service_credential)` builds the headers for one call:

| Header | Source |
|---|---|
| `X-Runefoble-Service-Credential` | The `service_credential` argument. Sent on every call. The name is `runefoble_platform.service_credential.SERVICE_CREDENTIAL_HEADER`. |
| `Authorization` | The `authorization` argument. Omitted when it is `None` or empty. |
| `traceparent` (and `tracestate`, when set) | The active OpenTelemetry context, through `runefoble_platform.telemetry.inject_trace_context`. |

No other header leaves the caller. Client headers are never copied. The owning service verifies the bearer token itself (ADR-0015, decision c). The service credential identifies the calling service. It is not a user token, and it does not replace the bearer token. The gateway does not send a principal or user header.

## Path segments

`path(*segments)` builds the path that `send` takes. It returns an absolute path, for example `path("api", "v1", "pins", "a/b?c")` returns `/api/v1/pins/a%2Fb%3Fc`.

- Each segment is percent-encoded with `urllib.parse.quote(segment, safe="")`. A `/`, `?`, or `#` stays inside one segment.
- It raises `ValueError` for an empty segment, or for a segment that is `.` or `..`. Such a segment would change the target route.

Use `path` for every segment that comes from user or agent input. Do not join raw strings into a path.

## Gateway status mapping

The gateway registers the handlers in `gateway_api/upstream_errors.py`. Every failure logs at warning level.

| Upstream result | Gateway response | Body |
|---|---|---|
| 2xx with JSON body | Same status, decoded JSON | Upstream JSON |
| 2xx with non-JSON body | `502` | `{"detail": "Upstream service returned an invalid response"}` |
| 4xx | Same status | Upstream body, unchanged, with its `content-type` |
| 5xx | `502` | `{"detail": "Upstream service is unavailable", "upstream": "<service>"}` |
| Connect failure or timeout | `503` | `{"detail": "Upstream service is unavailable", "upstream": "<service>"}` |
| No base URL configured | `503` | `{"detail": "Upstream service is unavailable", "upstream": "<service>"}` |

The gateway never returns a substitute body for any of these cases.

## Gateway registry

`gateway_api.upstreams.UpstreamRegistry` holds one `ServiceClient` for each service whose base URL is set.

- The FastAPI lifespan in `gateway_api/main.py` builds the registry from `PlatformSettings()` at start-up. It stores the registry on `app.state.upstreams`. It closes every client at shutdown.
- `gateway_api.dependencies.get_upstreams(request)` returns the registry. It is a FastAPI dependency.
- `registry.client(service)` returns the client. It raises `UpstreamUnavailableError` when no URL is configured for that service.
- The lifespan also reads `RUNEFOBLE_SERVICE_CREDENTIAL` (through `expected_service_credential`). The gateway refuses to start when it is unset or blank. Helm injects the value from the credentials Secret into `gateway-api`.

Service names and settings fields:

| Service name | `PlatformSettings` field | Environment variable |
|---|---|---|
| `game_session` | `game_session_url` | `RUNEFOBLE_GAME_SESSION_URL` |
| `board_state` | `board_state_url` | `RUNEFOBLE_BOARD_STATE_URL` |
| `the_watcher` | `the_watcher_url` | `RUNEFOBLE_THE_WATCHER_URL` |
| `character_sheet` | `character_sheet_url` | `CHARACTER_SHEET_URL` |
| `campaign_lore` | `campaign_lore_url` | `CAMPAIGN_LORE_URL` |
| `campaign_analytics` | `campaign_analytics_url` | `CAMPAIGN_ANALYTICS_URL` |
| `soundscape` | `soundscape_url` | `SOUNDSCAPE_SERVICE_URL` |
| `rules_compendium` | `rules_compendium_url` | `RUNEFOBLE_RULES_COMPENDIUM_URL` |
| `asset_forge` | `asset_forge_url` | `RUNEFOBLE_ASSET_FORGE_URL` |
| `voice_agent` | `voice_agent_url` | `RUNEFOBLE_VOICE_AGENT_URL` |
| `audience_studio` | `audience_studio_url` | `RUNEFOBLE_AUDIENCE_STUDIO_URL` |

The `character_sheet_url`, `campaign_lore_url`, `campaign_analytics_url`, and `soundscape_url` fields default to the in-cluster addresses in the Helm chart (`services.yaml`). The other seven default to `None`. Helm renders only the four defaulted fields for `gateway-api` today.

## Related

- How-to: [Call Owning Services Through the Gateway](../how-to/call-owning-services-through-the-gateway.md)
- [Ports & Endpoints Routing Table](ports-and-endpoints.md#gateway-proxy-identity-and-errors)
- ADR-0015 (audit remediation decisions), decision (b): one shared typed client, no substitute values.
