# Reference: Identity and Token Contract

This page states the identity contract for every surface of the platform. It describes the code as it is now. Each claim names the code that enforces it.

Governing records: ADR-0015 (decisions c, d, e), PRD-0023, US-0062.

---

## 1. Token Settings

Zitadel is the only token issuer. The platform reads three settings. The JWKS (signing key) URL has no setting. The verifier reads it from OIDC discovery.

| Setting | Field | Value in code | Value in the Helm chart | Meaning |
|---|---|---|---|---|
| `RUNEFOBLE_ZITADEL_ISSUER` | `zitadel_issuer` | Default `http://localhost:8080` (`libs/runefoble_platform/src/runefoble_platform/config.py`) | `http://auth.localhost`, built from `zitadel.externalDomain`, `externalPort`, and `externalSecure` (`deployments/helm/runefoble/templates/_helpers.tpl`) | The browser-facing issuer. The token `iss` claim must equal it exactly. |
| `RUNEFOBLE_ZITADEL_AUDIENCE` | `zitadel_audience` | Empty. When empty, the setting takes the value of `RUNEFOBLE_ZITADEL_CLIENT_ID` (default `runefoble-api`) (`config.py`, validator `_default_audience_to_client_id`). | Read from the `project-id` key of the Secret `runefoble-zitadel-client` (`_helpers.tpl`). | The expected `aud` claim. In a cluster, it is the Zitadel project ID. |
| `RUNEFOBLE_ZITADEL_INTERNAL_URL` | `zitadel_internal_url` | Unset (`None`) | `http://zitadel:<port>` (`_helpers.tpl`) | Optional. The in-cluster origin for discovery and JWKS requests. |

Rules:

- The verifier accepts only `RS256` signatures (`libs/runefoble_auth/src/runefoble_auth/zitadel.py`, `ACCEPTED_ALGORITHMS`).
- The verifier requires the claims `exp`, `sub`, `iss`, and `aud` (`zitadel.py`, `REQUIRED_CLAIMS`).
- The `iss` and `aud` checks are exact matches (`zitadel.py`, `verify_token`).
- Discovery reads `<issuer>/.well-known/openid-configuration`. The `jwks_uri` in that document is the JWKS URL (`zitadel.py`, `discover_jwks_url`).
- When `RUNEFOBLE_ZITADEL_INTERNAL_URL` is set, discovery and JWKS requests go to that origin. Each request sends `Host` set to the issuer host. Zitadel refuses other hosts. The `iss` check still uses the issuer value (`zitadel.py`, `issuer_host_headers`, `_rebase`).
- A verifier built directly with a blank issuer or audience raises `ConfigurationError` (`zitadel.py`, `__init__`).
- No setting turns off verification. `RUNEFOBLE_AUTH_DEV_MODE` and `AUTH_DEV_MODE` have no effect (CHANGELOG, TASK-0520).
- The audience setting also reads the unprefixed name `ZITADEL_AUDIENCE` (`config.py`, `AliasChoices`).

---

## 2. Surface Rules

### HTTP

- A request carries identity only in `Authorization: Bearer <jwt>`.
- The scheme must be exactly `Bearer`. An empty token counts as missing (`libs/runefoble_auth/src/runefoble_auth/principal.py`, `bearer_token_from_authorization`).
- The principal dependency is `require_principal`. Each service binds it through `runefoble_auth.wiring.build_identity_dependencies`.

### WebSocket

- A browser cannot set `Authorization` on a WebSocket. The client offers two subprotocols:
  1. `runefoble.v1`
  2. `runefoble.bearer.<jwt>`
- The server reads the token from the bearer subprotocol (`libs/runefoble_auth/src/runefoble_auth/websocket.py`, `bearer_token_from_subprotocols`).
- The server accepts the handshake with `runefoble.v1` only (`websocket.py`, `RUNEFOBLE_SUBPROTOCOL`).
- A token in the URL query string is never read.
- Every WebSocket route calls `admit_websocket` before it accepts the socket (`websocket.py`, `admit_websocket`).

### Service to Service

- A calling service sends the header `X-Runefoble-Service-Credential`. The value comes from `RUNEFOBLE_SERVICE_CREDENTIAL` (`libs/runefoble_platform/src/runefoble_platform/service_credential.py`).
- The receiver compares the value in constant time (`service_credential.py`, `service_credential_matches`).
- The service credential has no user id. The caller identity has `user_id=None` and `via_service_credential=True` (`libs/runefoble_auth/src/runefoble_auth/caller.py`).
- A request that carries an `Authorization` header must verify as a user token. A failed user token returns `401`, even when the service credential is also present (`caller.py`).
- A Zitadel user token is not a service credential. The inference worker accepts only the service credential (`services/inference_worker/src/inference_worker/auth.py`).
- A service credential never acts for a user. Routes that act for a user use `require_principal`, so a service call cannot reach them (`caller.py`, module docstring).

Service credential receivers (routes that accept `get_caller_or_service`):

| Service | Code |
|---|---|
| `board_state` | `services/board_state/src/board_state/dependencies.py`, `routers/boards.py` |
| `character_sheet` | `services/character_sheet/src/character_sheet/dependencies.py` |
| `game_session` | `services/game_session/src/game_session/settlement/auth/tokens.py`, `routers/session_auth.py`, `routers/chronicle.py` |
| `rules_compendium` | `services/rules_compendium/src/rules_compendium/dependencies.py`, `routers/rules.py`, `routers/encounters.py` |
| `inference_worker` | `services/inference_worker/src/inference_worker/auth.py` (its own guard) |

Service credential senders:

| Service | Code |
|---|---|
| `gateway-api` (shared service client) | `gateway/api/src/gateway_api/upstreams.py` |
| `gateway-mcp` | `gateway/mcp/src/gateway_mcp/owning_services.py` |
| `the_watcher` | `services/the_watcher/src/the_watcher/worker_client.py` |
| `game_session` (character client) | `services/game_session/src/game_session/character_client.py` |
| `campaign_lore` (stronghold client) | `services/campaign_lore/src/campaign_lore/stronghold_client.py` |

The following services verify only user tokens. They pass `None` for the service credential in `build_identity_dependencies`: `gateway-api`, `the_watcher`, `campaign_lore`, `voice_agent`, `asset_forge`, `campaign_analytics`, and `soundscape`.

---

## 3. Subject

- The token `sub` claim is the user id. The verifier returns it as `VerifiedPrincipal.user_id` (`zitadel.py`, `_principal_from_claims`).
- `username` comes from `preferred_username`. When that claim is absent, `username` is the `sub` value.
- `email` comes from the `email` claim. It is `None` when the claim is absent.
- `VerifiedPrincipal` has three fields: `user_id`, `username`, and `email` (`principal.py`). It has no roles and no admin flag.
- Roles and admin flags in a token grant nothing. No code reads them for authorization. Authorization uses only SpiceDB relations in `libs/runefoble_auth/schema/runefoble.zed` (ADR-0015 d, Hard Invariant 1).
- Token claims never write a SpiceDB relation. The claim sync route was removed (TASK-0534). See [SpiceDB and Zitadel Identity Sync](spicedb-zitadel-identity-sync.md).
- Identity headers and fields do not set the caller. Examples are `X-User-Id`, `x-user-id`, a `user_id` query parameter, and a body field such as `author_id` or `user_id`. Services ignore them (for example `services/the_watcher/src/the_watcher/identity.py`, module docstring).

---

## 4. Public Routes

Only the routes in this section take no identity check. Every other route verifies a bearer token, or it forwards the bearer to an owning service that verifies it.

### Gateway (`gateway-api`)

| Route | Identity | Code |
|---|---|---|
| `GET /health`, `GET /healthz`, `GET /api/v1/health`, `GET /readyz` | None | `gateway/api/src/gateway_api/routers/health.py` |
| `GET /openapi.json`, `GET /docs`, `GET /redoc` | None | `gateway/api/src/gateway_api/main.py` |
| `GET /api/v1/auth/sync/health` | None | `gateway/api/src/gateway_api/auth_sync.py` |
The spectator and overlay reads are not public. `GET /api/v1/spectate/{session_id}` and `GET /overlay/party-vitals/{session_id}` need a verified `Authorization: Bearer` token and `session.observe` on the session (`gateway/api/src/gateway_api/routers/spectator.py`, `gateway/api/src/gateway_api/routers/overlay.py`). A missing or failed token returns `401`. A viewer without the permission gets `403`. The state comes from `game_session` and `board_state`, and each owner removes the private fields before the gateway reads them. An owner `404` passes on unchanged. The `token` query parameter is not read.

Proxy routes:

- A proxy route forwards the caller's `Authorization` header to the owning service. It sends no other client header (`gateway/api/src/gateway_api/proxy.py`).
- The owning service verifies the token again (ADR-0015 c).
- Some proxy routes have no gateway identity dependency. Examples are `/api/v1/assets/*`, `/api/v1/forge/*`, `/api/v1/voice/*`, and `/api/v1/mobile/companion/*` (`gateway/api/src/gateway_api/routers/voice_proxy.py`, `assets_proxy.py`, `forge_proxy.py`). For these routes the owning service is the only identity check.

### Owning services

Each owning service keeps its own short public list. The lists are in [Ports and Endpoints](ports-and-endpoints.md):

- `voice-agent`: `GET /healthz` and `GET /ui/manifest`.
- `campaign-lore`: `GET /health`, `GET /healthz`, `GET /openapi.json`, and `GET /ui/manifest`.
- `asset-forge`, `soundscape`, and `character-sheet`: `GET /healthz`, `GET /health`, `GET /ui/manifest`, and `GET /openapi.json`.

---

## 5. Error Shape and Status

### HTTP

| Status | When | Body and headers | Code |
|---|---|---|---|
| `401` | No `Authorization` header, a non-Bearer scheme, an empty token, a failed verification, or a service call that fails the credential check | `{"error": "unauthorized", "message": "..."}` and `WWW-Authenticate: Bearer` | `libs/runefoble_auth/src/runefoble_auth/principal.py` (`unauthorized`), `caller.py` |
| `403` | The token is valid, but the SpiceDB check denies the action | Proxy routes pass the owner's body through. Composite routes and the routes that keep a gateway check answer the `require_zanzibar_permission` body | `gateway/api/src/gateway_api/auth.py` (`require_zanzibar_permission`), owner checks in each service |
| `503` | SpiceDB cannot answer, or a SpiceDB write was not applied (any `AuthzError`) | `{"error": "authorization_unavailable"}` | `libs/runefoble_auth/src/runefoble_auth/authz_http.py` |
| `500` | A schema name is missing from `runefoble.zed` | `{"error": "authorization_schema_error", "error_id": "<uuid>"}`. The gRPC detail stays in the log. | `authz_http.py` |
| `503` | An owning service is unreachable, or the call times out | `{"detail", "upstream"}` | `gateway/api/src/gateway_api/upstream_errors.py` |
| `502` | An owning service returns a 5xx, or a 2xx reply is not JSON | `{"detail", "upstream"}` | `upstream_errors.py`, `proxy.py` |
| Upstream 4xx | Passed through with the same status and body | As the owning service sent | `upstream_errors.py` |

A discovery or JWKS fetch failure is not a `401`, a `502`, or a `503` today. The verifier raises a `URLError` that no handler maps. In-process, `ZitadelAuthService.verify_token` with an unreachable issuer raises that error. This is a known gap.

### WebSocket

| Close code | When | Code |
|---|---|---|
| `1008` | No valid bearer subprotocol. The socket closes before accept. | `websocket.py` (`WS_POLICY_VIOLATION`) |
| `4403` | The token is valid, but the permission check denies the action | `websocket.py` (`WS_AUTHORIZATION_REFUSED`) |
| `1011` | SpiceDB cannot answer. A failed check is never a denial. | `websocket.py` (`WS_AUTHORIZATION_UNAVAILABLE`) |

Per-message refusals use `send_socket_error` with codes such as `PERMISSION_DENIED` and `UNKNOWN_ACTION` (`websocket.py`).

---

## 6. Removed Routes and Replacements

The paths in this table are absent from `/openapi.json` of `gateway-api`. Use the replacement.

| Removed route or behavior | Former behavior | Replacement | Removed by |
|---|---|---|---|
| `POST /api/v1/auth/token` | Issued a self-signed token for any user name and password. Roles came from the name. | Zitadel OIDC authorization code with PKCE (`frontend/src/auth/oidc-client.ts`) | TASK-0523 |
| `POST /api/v1/auth/refresh` | Minted a fixed token | Refresh token grant in the App Shell (`frontend/src/auth/oidc-client.ts`, `refresh_token` grant) | TASK-0523 |
| `POST /api/v1/auth/logout` | No action | End-session redirect with `id_token_hint` (`oidc-client.ts`) | TASK-0523 |
| `POST /api/v1/auth/register`, `/verify`, `/verify-email`, `/resend-verification` | In-app sign-up with in-memory state | Zitadel hosted sign-up. The App Shell sends `prompt=create` (`oidc-client.ts`) | TASK-0523, TASK-0524 |
| `POST /api/v1/auth/admin/seed` | Returned an admin bearer with no authentication | None. Zitadel users only. | TASK-0523 |
| `POST /api/v1/auth/admin/invite` | Invite dispatch with no authentication | `POST /api/v1/campaigns/{campaign_id}/invites` and `POST /api/v1/campaigns/join` | TASK-0523 |
| `POST /api/v1/auth/dev/send-test`, `POST /api/v1/auth/test-email`, `DELETE /api/v1/auth/dev/emails` (test mail routes) | Let any caller send or clear test mail | Read captured mail in Mailpit at `/mail` ([Test Email Signups with Mailpit](../how-to/test-email-signups-with-mailpit.md)) | TASK-0523 |
| `POST /api/v1/auth/sync/user` | Wrote campaign roles from body claims with no authentication | None. Token claims grant no relation. | TASK-0534 |
| `POST /api/v1/auth/sync/membership`, `/character-ownership`, `/token-binding` | Wrote SpiceDB tuples with no authentication | `POST /api/v1/campaigns/{id}/roles`, `POST /api/v1/characters`, `POST /api/v1/campaigns/join` | TASK-0543 |
| `runefoble-dev-signature` signing key and the `dev-user-001` fallback | Signed or accepted development tokens | Zitadel RS256 tokens only | TASK-0520, TASK-0523 |
| `RUNEFOBLE_AUTH_DEV_MODE`, `AUTH_DEV_MODE` | Turned off verification | None. No setting disables verification. | TASK-0520 |
| `X-User-Id` and `x-user-id` identity | Set the caller | `Authorization: Bearer <jwt>` | TASK-0521, TASK-0529 |
| `?user_id=`, `?token=`, and `guest_user` on WebSocket routes | Set the caller on a socket | Bearer subprotocol `runefoble.bearer.<jwt>` | TASK-0522 |

---

## 7. Other Identity Settings

| Setting | Use | Code |
|---|---|---|
| `RUNEFOBLE_SERVICE_CREDENTIAL` | Shared service credential. No default. A receiver refuses to start without it. | `config.py`, `service_credential.py` (`expected_service_credential`) |
| `RUNEFOBLE_ZITADEL_CLIENT_ID` | Default audience when `RUNEFOBLE_ZITADEL_AUDIENCE` is empty | `config.py` |
| `RUNEFOBLE_SPICEDB_PRESHARED_KEY` | Key for SpiceDB. No default. | `config.py`, `libs/runefoble_auth/src/runefoble_auth/factory.py` |

---

## 8. Tests

| Surface | Test |
|---|---|
| Verifier and HTTP dependency | `libs/runefoble_auth/tests/test_verified_principal.py` |
| Gateway HTTP bearer and JWKS | `tests/test_blackbox_zitadel_http_auth.py` |
| Gateway WebSocket handshake | `tests/test_blackbox_zitadel_websocket_auth.py` |
| game_session, The Watcher, and inference worker | `tests/test_blackbox_service_identity.py` |
| Negative matrix for every surface | `tests/test_blackbox_identity_negative.py` (Gherkin mirror: `e2e/features/identity-negative.feature`) |
| Retired routes are absent | `tests/test_blackbox_auth_routes_retired.py` |
| Signed test tokens | `libs/runefoble_auth/src/runefoble_auth/testing/signing_test_issuer.py` |

---

## See Also

- [Authenticate Users with Zitadel OIDC and JWTs](../how-to/authenticate-with-zitadel-oidc.md)
- [Verify Identity in FastAPI and WebSockets](../how-to/verify-identity-in-fastapi-and-websockets.md)
- [Ports and Endpoints](ports-and-endpoints.md)
- [Platform Services](platform-services.md)
- [SpiceDB and Zitadel Identity Sync](spicedb-zitadel-identity-sync.md)
