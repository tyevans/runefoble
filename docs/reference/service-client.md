# Reference: Service Client

The shared typed HTTP client for calls from a gateway to an owning bounded context. It lives in `libs/runefoble_platform/src/runefoble_platform/service_client/`.

The gateway uses this client for every proxy call. Each proxy call goes through `gateway_api.proxy.forward_json` for a JSON body that the gateway builds, or `forward_bytes` for a raw body that the owner validates, a binary reply (PDF, PNG, STL), or an upload (TASK-0595). `forward_bytes` is the only raw-body path. All use the registry in `gateway_api.upstreams`. The MCP gateway uses it through the route helpers in `gateway_mcp.owning_services.OwningServices`. Those helpers map the errors to MCP tool errors. They keep one client for each event loop, service, and base URL.

## Modules

| Module | Contents |
|---|---|
| `client.py` | `ServiceClient`, `UpstreamReply` |
| `errors.py` | `UpstreamError`, `UpstreamUnavailableError`, `UpstreamFailureError` |
| `headers.py` | `build_upstream_headers` |
| `health.py` | `ProbeStatus`, `probe_health` |
| `paths.py` | `path` |

The package exports `ServiceClient`, `UpstreamReply`, `UpstreamError`, `UpstreamUnavailableError`, `UpstreamFailureError`, `ProbeStatus`, `probe_health`, and `path`.

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
    content: bytes | None = None,
    content_type: str | None = None,
) -> UpstreamReply
```

| Argument | Meaning |
|---|---|
| `method` | HTTP method, for example `GET` or `POST`. |
| `path` | Path that is appended to `base_url`, for example `/api/v1/soundscape/cue`. Build it with `path(...)` when a segment comes from input. |
| `authorization` | The verified `Authorization` header value of the caller, or `None`. |
| `timeout_s` | Timeout for this call, in seconds. It applies to connect, read, write, and pool. |
| `json` | Optional JSON body that the gateway built. |
| `params` | Optional query string values. |
| `content` | Optional raw body, forwarded unchanged. The owner parses it. Pass `json` or `content`, not both. |
| `content_type` | Media type of `content`. The client sends it only with `content`. |

The caller sets `timeout_s` for each call. The client sets no default timeout. The client does not retry. The client does not cache.

### `websocket_target`

```python
client.websocket_target(path: str) -> tuple[str, dict[str, str]]
```

Returns the `ws://` or `wss://` URL for `path` on the owner, and the handshake headers. The headers carry the service credential only. The caller's bearer goes in the subprotocol list, so the owner verifies the token that the client offered. The gateway uses it through `gateway_api.websocket_relay` (TASK-0592).

## `UpstreamReply`

A frozen dataclass. It holds an upstream 2xx or 4xx answer without change.

| Field | Type | Meaning |
|---|---|---|
| `status_code` | `int` | Status code from the owning service. |
| `content_type` | `str` | `content-type` header from the owning service. Defaults to `application/json`. |
| `body` | `bytes` | Raw response body. |
| `www_authenticate` | `str \| None` | `WWW-Authenticate` header from the owning service, if any. |
| `relayed_headers` | `tuple[tuple[str, str], ...]` | Payload headers of the reply, such as `Content-Disposition` and `X-*`. Transport headers are dropped: `Content-Length`, `Content-Encoding`, `Transfer-Encoding`, `Connection`, `Keep-Alive`, `Set-Cookie`, `WWW-Authenticate`, and `Content-Type`. |

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
| 2xx with JSON body (`forward_json`) | Same status, decoded JSON | Upstream JSON |
| 2xx with non-JSON body (`forward_json`) | `502` | `{"detail": "Upstream service returned an invalid response"}` |
| 2xx from `forward_bytes` (raw body or binary) | Same status, same `content-type`, same body bytes, relayed headers | Upstream bytes |
| 4xx | Same status | Upstream body, unchanged, with its `content-type` and its `WWW-Authenticate` challenge |
| 5xx | `502` | `{"detail": "Upstream service is unavailable", "upstream": "<service>"}` |
| Connect failure or timeout | `503` | `{"detail": "Upstream service is unavailable", "upstream": "<service>"}` |
| No base URL configured | `503` | `{"detail": "Upstream service is unavailable", "upstream": "<service>"}` |

The gateway never returns a substitute body for any of these cases.

## Health probes

`probe_health(client, *, timeout_s)` sends `GET /healthz` through a `ServiceClient` and returns a `ProbeStatus`. It caches nothing. The gateway calls it for each downstream service on every `GET /healthz`.

| Probe result | `ProbeStatus` value |
|---|---|
| `client` is `None` (no base URL is configured) | `not_configured` |
| HTTP 200 | `operational` |
| Any other HTTP status, including 4xx and 5xx | `degraded` |
| Timeout or connection error (`UpstreamUnavailableError`) | `unreachable` |

The probe sends no `Authorization` header. It sends the service credential and the trace context, like every call.

## Gateway registry

`gateway_api.upstreams.UpstreamRegistry` holds one `ServiceClient` for each service whose base URL is set.

- The FastAPI lifespan in `gateway_api/main.py` builds the registry from `PlatformSettings()` at start-up. It stores the registry on `app.state.upstreams`. It closes every client at shutdown.
- `gateway_api.dependencies.get_upstreams(request)` returns the registry. It is a FastAPI dependency.
- `registry.client(service)` returns the client. It raises `UpstreamUnavailableError` when no URL is configured for that service.
- `registry.find(service)` returns the client, or `None` when no URL is configured. Use it when a missing URL is a normal result, as in the health probes.
- `registry.health_probe_timeout_s` is the timeout for each health probe. It comes from `RUNEFOBLE_GATEWAY_HEALTH_PROBE_TIMEOUT_S` (default `1.0`).
- The lifespan also reads `RUNEFOBLE_SERVICE_CREDENTIAL` (through `expected_service_credential`). The gateway refuses to start when it is unset or blank. Helm injects the value from the credentials Secret into `gateway-api`.

Service names and settings fields:

| Service name | `PlatformSettings` field | Environment variable |
|---|---|---|
| `game_session` | `game_session_url` | `RUNEFOBLE_GAME_SESSION_URL` |
| `board_state` | `board_state_url` | `RUNEFOBLE_BOARD_STATE_URL` |
| `the_watcher` | `the_watcher_url` | `RUNEFOBLE_WATCHER_URL` |
| `character_sheet` | `character_sheet_url` | `RUNEFOBLE_CHARACTER_SHEET_URL` |
| `campaign_lore` | `campaign_lore_url` | `CAMPAIGN_LORE_URL` |
| `campaign_analytics` | `campaign_analytics_url` | `CAMPAIGN_ANALYTICS_URL` |
| `soundscape` | `soundscape_url` | `SOUNDSCAPE_SERVICE_URL` |
| `rules_compendium` | `rules_compendium_url` | `RUNEFOBLE_RULES_COMPENDIUM_URL` |
| `asset_forge` | `asset_forge_url` | `RUNEFOBLE_ASSET_FORGE_URL` |
| `voice_agent` | `voice_agent_url` | `RUNEFOBLE_VOICE_AGENT_URL` |
| `audience_studio` | `audience_studio_url` | `RUNEFOBLE_AUDIENCE_STUDIO_URL` |

`campaign_analytics_url` and `soundscape_url` default to their in-cluster addresses. Every other field defaults to `None`. A field left at `None` means no route: a proxy call returns `503`, and a health probe reports `not_configured`. `character_sheet_url` has no default (TASK-0674). The Helm chart renders these variables for `gateway-api` in `templates/services.yaml`: `RUNEFOBLE_GAME_SESSION_URL`, `RUNEFOBLE_WATCHER_URL`, `RUNEFOBLE_BOARD_STATE_URL`, `RUNEFOBLE_CHARACTER_SHEET_URL`, `RUNEFOBLE_VOICE_AGENT_URL`, `CAMPAIGN_LORE_URL`, `CAMPAIGN_ANALYTICS_URL`, `SOUNDSCAPE_SERVICE_URL`, `RUNEFOBLE_RULES_COMPENDIUM_URL`, and `RUNEFOBLE_ASSET_FORGE_URL`.

## Related

- How-to: [Call Owning Services Through the Gateway](../how-to/call-owning-services-through-the-gateway.md)
- [Ports & Endpoints Routing Table](ports-and-endpoints.md#gateway-proxy-identity-and-errors)
- ADR-0015 (audit remediation decisions), decision (b): one shared typed client, no substitute values.
