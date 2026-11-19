# Reference: Service Client

The shared typed HTTP client for calls from a gateway to an owning bounded context. It lives in `libs/runefoble_platform/src/runefoble_platform/service_client/`.

The gateway uses this client for every proxy call. Each proxy call goes through `gateway_api.proxy.forward_json` for a JSON body that the gateway builds, or `forward_bytes` for a raw body that the owner validates, a binary reply (PDF, PNG, STL), or an upload (TASK-0595). `forward_bytes` is the only raw-body path. All use the registry in `gateway_api.upstreams`. The MCP gateway uses it through the route helpers in `gateway_mcp.owning_services.OwningServices`. Those helpers map the errors to MCP tool errors. They keep one client for each event loop, service, and base URL. The client pool belongs to the gateway MCP container, so each app has its own pool (TASK-0746).

## Modules

| Module | Contents |
|---|---|
| `client.py` | `ServiceClient`, `UpstreamReply` |
| `errors.py` | `UpstreamError`, `UpstreamUnavailableError`, `UpstreamFailureError` |
| `headers.py` | `build_upstream_headers` |
| `health.py` | `ProbeStatus`, `probe_health` |
| `owners.py` | `OWNER_URL_FIELDS`: the owner service names and their settings fields |
| `owner_routes.py` | `OwnerRoute` and one function for each shared owner route |
| `paths.py` | `path` |
| `replies.py` | `decode_json_body`, `error_detail` |

The package exports `ServiceClient`, `UpstreamReply`, `UpstreamError`, `UpstreamUnavailableError`, `UpstreamFailureError`, `ProbeStatus`, `probe_health`, `path`, `OWNER_URL_FIELDS`, `OwnerRoute`, `decode_json_body`, and `error_detail`. The module `owner_routes` is imported by name.

## Owner routes

`owner_routes` holds one function for each owner route that the MCP gateway calls, and each route that a gateway module builds by path (TASK-0861). Each function returns an `OwnerRoute(method, path)`. The caller sends the body. Both gateways use these functions, so a route has one definition. Each function takes the path values of its route as strings.

| Function | Route |
|---|---|
| `get_campaign(campaign_id)` | `GET /api/v1/campaigns/{id}` (game_session) |
| `get_session(session_id)` | `GET /api/v1/sessions/{id}` (game_session) |
| `join_session(session_id)` | `POST /api/v1/sessions/{id}/join` (game_session) |
| `start_encounter(session_id)` | `POST /api/v1/sessions/{id}/encounters/start` (game_session) |
| `get_combat_state(session_id)` | `GET /api/v1/sessions/{id}/combat` (game_session) |
| `list_characters()` | `GET /api/v1/characters` (character_sheet) |
| `create_character()` | `POST /api/v1/characters` (character_sheet) |
| `get_character(character_id)` | `GET /api/v1/characters/{id}` (character_sheet) |
| `assign_campaign(character_id)` | `PATCH /api/v1/characters/{id}/campaign` |
| `change_health(character_id)` | `POST /api/v1/characters/{id}/health` |
| `apply_penalty(character_id)` | `POST /api/v1/characters/{id}/penalties` |
| `apply_condition(character_id)` | `POST /api/v1/characters/{id}/conditions` |
| `remove_condition(character_id, condition)` | `DELETE /api/v1/characters/{id}/conditions/{condition}` |
| `cast_spell(character_id)` | `POST /api/v1/characters/{id}/spells/cast` |
| `prepare_spell(character_id)` | `POST /api/v1/characters/{id}/spells/prepare` |
| `equip_item(character_id)` | `POST /api/v1/characters/{id}/equipment` |
| `unequip_item(character_id, slot)` | `DELETE /api/v1/characters/{id}/equipment/{slot}` |
| `add_inventory_item(character_id)` | `POST /api/v1/characters/{id}/inventory` |
| `remove_inventory_item(character_id, item_id)` | `DELETE /api/v1/characters/{id}/inventory/{item_id}` |
| `get_guardrails(character_id)` | `GET /api/v1/characters/{id}/guardrails` |
| `update_guardrails(character_id)` | `PUT /api/v1/characters/{id}/guardrails` |
| `get_board(session_id)` | `GET /api/v1/boards/{session_id}` (board_state) |
| `get_token(session_id, token_id)` | `GET /api/v1/boards/{session_id}/tokens/{token_id}` (board_state) |
| `place_token(session_id)` | `POST /api/v1/boards/{session_id}/tokens` (board_state) |
| `move_token(session_id, token_id)` | `POST /api/v1/boards/{session_id}/tokens/{token_id}/move` (board_state) |
| `narrate()` | `POST /api/v1/watcher/narrate` (the_watcher) |
| `propose_action()` | `POST /api/v1/watcher/actions/propose` (the_watcher) |
| `get_monster(name)` | `GET /api/v1/compendium/monsters/{name}` (rules_compendium) |
| `balance_encounter()` | `POST /api/v1/compendium/encounters/balance` (rules_compendium) |

Path segments are encoded with `path()`. A value cannot change the route. A value that `path()` refuses (`.`, `..`, or empty) raises `ValueError`. The gateway maps that to `404` before it calls the owner (`owner_route` in `gateway_api.proxy`, and the `owner` option of `ProxyRoute`).

## Gateway proxy table

A pure pass-through route is a row of `ProxyRoute` in `gateway_api/proxy_table.py`. Each module in `gateway_api/routers/` that holds only pass-through routes lists its rows in `ROUTES` and calls `register_proxy_routes(router, ROUTES)`. A row names the method, the public path, the owner path, the service, the reply mode (`json` or `bytes`), the body mode (`none`, `raw`, or `json`), the query mode, the caller check, and the timeout. The generated endpoint declares its path parameters, query defaults, and body to FastAPI, so the OpenAPI document keeps the same parameters and schemas.

The owner path is either `owner` (a function of `owner_routes`, so the path has one definition) or `owner_segments` (a tuple, where `{name}` takes a path parameter). Give exactly one. Use `owner` whenever `owner_routes` has a function for the route. A function takes the path parameters of the public path, by name.

The caller check of a row (`principal=True`) verifies the bearer token only. A route with a Zanzibar permission check, a transform, a typed reply, or a second owner call stays hand-written. Examples: the haggling route in `downtime_proxy.py`, and the session routes in `sessions_proxy.py`, which check a permission on each route.

A row whose owner path has a segment that the owner cannot encode (`.`, `..`, or empty) returns `404`.

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

Service names and settings fields. The map `OWNER_URL_FIELDS` in `runefoble_platform.service_client.owners` is the one source. Both gateways read it:

| Service name | `PlatformSettings` field | Environment variable |
|---|---|---|
| `game_session` | `game_session_url` | `RUNEFOBLE_GAME_SESSION_URL` |
| `board_state` | `board_state_url` | `RUNEFOBLE_BOARD_STATE_URL` |
| `the_watcher` | `the_watcher_url` | `RUNEFOBLE_WATCHER_URL` |
| `character_sheet` | `character_sheet_url` | `RUNEFOBLE_CHARACTER_SHEET_URL` |
| `campaign_lore` | `campaign_lore_url` | `RUNEFOBLE_CAMPAIGN_LORE_URL` |
| `campaign_analytics` | `campaign_analytics_url` | `RUNEFOBLE_CAMPAIGN_ANALYTICS_URL` |
| `soundscape` | `soundscape_url` | `RUNEFOBLE_SOUNDSCAPE_URL` |
| `rules_compendium` | `rules_compendium_url` | `RUNEFOBLE_RULES_COMPENDIUM_URL` |
| `asset_forge` | `asset_forge_url` | `RUNEFOBLE_ASSET_FORGE_URL` |
| `voice_agent` | `voice_agent_url` | `RUNEFOBLE_VOICE_AGENT_URL` |
| `audience_studio` | `audience_studio_url` | `RUNEFOBLE_AUDIENCE_STUDIO_URL` |

Every service URL field defaults to `None`. No field has an in-cluster code default. A field left at `None` means no route: a proxy call returns `503`, and a health probe reports `not_configured`. Each variable is named `RUNEFOBLE_<SERVICE>_URL`, so each service has one name in every process (TASK-0794). The Helm chart renders these variables for `gateway-api` in `templates/services.yaml`: `RUNEFOBLE_GAME_SESSION_URL`, `RUNEFOBLE_WATCHER_URL`, `RUNEFOBLE_BOARD_STATE_URL`, `RUNEFOBLE_CHARACTER_SHEET_URL`, `RUNEFOBLE_VOICE_AGENT_URL`, `RUNEFOBLE_CAMPAIGN_LORE_URL`, `RUNEFOBLE_CAMPAIGN_ANALYTICS_URL`, `RUNEFOBLE_SOUNDSCAPE_URL`, `RUNEFOBLE_RULES_COMPENDIUM_URL`, `RUNEFOBLE_ASSET_FORGE_URL`, and `RUNEFOBLE_AUDIENCE_STUDIO_URL`.

## Related

- How-to: [Call Owning Services Through the Gateway](../how-to/call-owning-services-through-the-gateway.md)
- ADR-0015 (audit remediation decisions), decision (b): the gateway holds no substitute value.
- [Ports & Endpoints Routing Table](ports-and-endpoints.md#gateway-proxy-identity-and-errors)
- ADR-0015 (audit remediation decisions), decision (b): one shared typed client, no substitute values.
