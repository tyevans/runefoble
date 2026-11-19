# How-To: Verify Identity in FastAPI and WebSockets

## Purpose
Use this guide to protect a FastAPI HTTP route or WebSocket with a verified principal. The shared helpers live in `libs/runefoble_auth`. Every bounded context uses them. Do not write a new token parser. The surface rules, error codes, and removed routes are in [Identity and Token Contract](../reference/identity-and-token-contract.md).

## The Contract
- A **verified principal** is `VerifiedPrincipal(user_id, username, email)`.
- It has no roles and no admin flag. Roles are not authority. Use SpiceDB checks for permissions (ADR-0001).
- A request has identity only when its bearer token passes `ZitadelAuthService.verify_token`.
- Every failure raises a 401 (HTTP) or closes the handshake before accept (WebSocket). There is no fallback identity.

## Build the Identity Dependencies Once Per Service

`runefoble_auth.wiring` is the only place that builds identity dependencies. A service does not write its own verifier getter, setter, or user-id helper. Three steps:

1. `make_verifier_holder(build)` returns `(get, set)` for the process verifier. `get` builds it on first use. `set` replaces it, which tests use to trust a signing issuer.
2. `build_identity_dependencies(get_verifier, service_credential)` returns the route dependencies: `get_principal`, `CallerPrincipal`, `CallerId`, `get_caller_or_service`, and `CallerOrService`.
3. The service module binds those names. Routes import them from the service module.

`service_credential` is the value that this service accepts from other services (ADR-0015 e). Pass `expected_service_credential()` when the service receives service calls. Pass `None` when it does not. A `None` value refuses every service-credential request with `401`. User bearer requests still work.

```python
from typing import Annotated

from fastapi import Depends, FastAPI
from runefoble_auth.principal import VerifiedPrincipal
from runefoble_auth.wiring import (
    build_identity_dependencies,
    make_verifier_holder,
    verifier_from_settings,
)
from runefoble_platform.config import PlatformSettings

get_zitadel_auth_service, set_zitadel_auth_service = make_verifier_holder(
    lambda: verifier_from_settings(PlatformSettings())
)
get_principal, CallerPrincipal, CallerId, get_caller_or_service, CallerOrService = (
    build_identity_dependencies(get_zitadel_auth_service, None)
)

app = FastAPI()


@app.get("/api/v1/example")
def example(principal: Annotated[VerifiedPrincipal, Depends(get_principal)]):
    return {"user_id": principal.user_id}
```

Behavior:
- Missing header, a non-Bearer scheme, an empty token, or any verification failure returns `401` with body `{"error": "unauthorized", "message": ...}` and header `WWW-Authenticate: Bearer`.
- On success the dependency sets `request.state.principal`.
- The dependency is synchronous. FastAPI runs it in a worker thread, so a JWKS fetch does not block the event loop.

To build the verifier by hand, for example in a test, use `ZitadelAuthService(issuer=..., audience=..., internal_url=...)`. All three arguments are required. A blank issuer or audience raises `ConfigurationError` when the object is built (`libs/runefoble_auth/src/runefoble_auth/zitadel.py`).

## Routers: Depend on the Router and Take a `CallerId`

Bounded contexts that serve many routes apply the principal dependency at router level. This protects every route in the router, including routes that do not read identity.

```python
from typing import Annotated

from fastapi import APIRouter, Depends
from game_session.shared.identity import CallerId, get_principal

router = APIRouter(dependencies=[Depends(get_principal)])


@router.post("/api/v1/example/{item_id}")
async def act(item_id: str, caller_id: CallerId):
    return {"acting_user": caller_id, "item": item_id}
```

- `CallerId` is the verified token subject as a string. Use it for every permission check.
- Do not add a query, header, or body field for identity. A forged value never reaches the route.
- Keep public routes (health, manifests, OpenAPI) on the app, not on a guarded router.
- WebSocket routes do not use `require_principal`. They call `admit_websocket` (below).
- A service that builds its app from explicit settings (`create_app(settings, ...)`) builds its verifier from those settings. It stores the verifier on `app.state.zitadel_verifier`. Its getter takes `request: Request` and returns `request.app.state.zitadel_verifier`. It passes that getter to `build_identity_dependencies`. Campaign Analytics does this (`services/campaign_analytics/src/campaign_analytics/dependencies.py`). A getter that takes no arguments also works.
- Every service exposes the same names: `get_principal`, `CallerPrincipal`, and `CallerId`. The Watcher binds them in `services/the_watcher/src/the_watcher/identity.py`. Campaign Lore binds them in `services/campaign_lore/src/campaign_lore/identity.py`. Voice Agent binds them in `services/voice_agent/src/voice_agent/auth.py`. The gateway binds them in `gateway/api/src/gateway_api/auth.py`.

## Routes That Another Service Calls: Accept the Service Credential

Use `get_caller_or_service` (`CallerOrService`) only on a route that another service calls and that does not act for a user. The MCP gateway calls such routes. The dependency accepts either:

- a verified user bearer in `Authorization`, which gives `CallerIdentity(user_id=<subject>)`; or
- the service credential in `X-Runefoble-Service-Credential`, which gives `CallerIdentity(user_id=None)`.

```python
from runefoble_platform.service_credential import expected_service_credential
from runefoble_auth.wiring import build_identity_dependencies

SERVICE_CREDENTIAL = expected_service_credential()  # refuses start-up when unset
get_principal, CallerPrincipal, CallerId, get_caller_or_service, CallerOrService = (
    build_identity_dependencies(get_zitadel_auth_service, SERVICE_CREDENTIAL)
)


@router.get("/api/v1/things/{thing_id}", dependencies=[Depends(get_caller_or_service)])
async def read_thing(thing_id: UUID): ...
```

Rules:
- A route with a user-scoped permission check keeps `get_principal` or a `CallerId`. A service call must never reach it.
- A route attaches the dependency per route. Do not put it on the router, because the router would then open every route in it to the service credential.
- A presented `Authorization` header that fails verification gives `401`, even when the service credential is also present.

## WebSocket: Use `admit_websocket`

Browsers cannot send `Authorization` on a WebSocket. The client offers two subprotocols:
- `runefoble.v1`
- `runefoble.bearer.<jwt>`

```python
from fastapi import WebSocket
from runefoble_auth.websocket import admit_websocket


async def ws_handler(websocket: WebSocket) -> None:
    principal = await admit_websocket(websocket, verifier)
    if principal is None:
        return  # Handshake refused and closed with 1008 before accept
    # Continue with principal.user_id
```

`runefoble_auth.websocket` is the only admission path. Every WebSocket route uses it. It has three parts:

| Helper | Use |
|---|---|
| `admit_websocket(websocket, verifier, authorize=None, *, denial_message=None)` | Verify the bearer, check the permission, then accept. Returns the principal or `None`. |
| `action_authorizer(action, resource_id)` | Build the `authorize` check for a schema action, such as `session.observe`, on one object. |
| `send_socket_error(websocket, code, message, **fields)` | Send a per-message error frame, such as `PERMISSION_DENIED` or `UNKNOWN_ACTION`. |

```python
from fastapi import WebSocket
from runefoble_auth.websocket import action_authorizer, admit_websocket


async def ws_handler(websocket: WebSocket, session_id: str) -> None:
    principal = await admit_websocket(
        websocket, verifier, action_authorizer("session.observe", session_id)
    )
    if principal is None:
        return  # Refused and closed before accept
    # Continue with principal.user_id
```

`admit_websocket` closes a refused handshake before accept and returns `None`. It logs the path and the outcome, never the token:
- No valid bearer: close `1008`.
- The bearer is valid, but the permission check returns false: close `4403`.
- SpiceDB cannot answer (`AuthzError`): close `1011`. A failed check is never a denial.

On success it accepts with `runefoble.v1`.

Pass `denial_message` when a client needs a reason before the close. The socket then accepts, sends a `PERMISSION_DENIED` frame with that message, and closes `4403`. The campaign and minigame sockets use this form.

For a check that needs more than one call, pass any async function that takes the user id and returns a bool. The board and speaker checks do this. A route that picks its own subprotocol at accept time calls `verify_websocket` instead. That call closes `1008` on failure and does not accept.

Rules:
- Call `admit_websocket` first. Do not accept the socket in the route before it.
- Use `action_authorizer` for a schema permission. Do not write a second permission check in a route.
- Send every per-message refusal with `send_socket_error`. Use the codes `PERMISSION_DENIED` and `UNKNOWN_ACTION`.
- Do not accept, then send an error, for an identity failure. The handshake is refused.
- Never read a token from the URL query string.
- Accept only `runefoble.v1` as the protocol echo.
- Run the loop with `serve_authorized_socket`. Do not write a receive loop by hand.

### Run the Socket Loop With `serve_authorized_socket`

The session, campaign, and overlay routes share one loop. `serve_authorized_socket` runs the whole life of an admitted socket:

```python
from runefoble_auth.websocket import action_authorizer, serve_authorized_socket

await serve_authorized_socket(
    websocket,
    admit=lambda ws: admit_gateway_websocket(ws, action_authorizer("session.observe", session_id)),
    on_open=open_room,  # register the socket, send "connected"; return False if refused
    on_frame=handle_frame,  # one call per inbound frame
    on_close=lambda: ws_manager.disconnect(session_id, websocket),  # always runs once
    receive=WebSocket.receive_text,  # default: WebSocket.receive_json
)
```

Do not write a second receive loop in a route. `on_close` runs in a `finally` block, so a finished socket always leaves its group.

### Keep Live Sockets in `WebSocketGroups`

`runefoble_platform.ws_groups.WebSocketGroups[K]` holds the live sockets of one room, keyed by session, campaign, table, or board. It offers `register`, `disconnect`, `broadcast`, and `clear`. A socket whose send fails is logged and removed from its group. The other sockets still receive the message. Create one instance per room kind at module level, for example `ws_manager = WebSocketGroups[str]()`.

## Test Both Paths With Signed Tokens

```python
from tests.helpers.signing_test_issuer import SigningTestIssuer

issuer = SigningTestIssuer()
verifier = issuer.verifier()
token = issuer.mint("user-evelyn")
client.get("/api/v1/example", headers={"Authorization": f"Bearer {token}"})
client.websocket_connect("/ws", subprotocols=["runefoble.v1", f"runefoble.bearer.{token}"])
```

Negative cases to cover: no token, garbage, HS256 with a known secret, `alg: none`, unsigned, unknown key, expired, wrong `aud`, wrong `iss`, missing `sub`. The reference suite is `libs/runefoble_auth/tests/test_verified_principal.py`.

## Configuration
- `RUNEFOBLE_ZITADEL_ISSUER` (`zitadel_issuer`): must equal the token `iss`. The settings default is `http://localhost:8080`, which is for local runs only. The Helm chart sets `http://auth.localhost`. Set the value in every deployed environment.
- `RUNEFOBLE_ZITADEL_AUDIENCE` (`zitadel_audience`): must equal the token `aud`. In a cluster it is the project ID from the Secret `runefoble-zitadel-client`. When it is empty, the settings use `RUNEFOBLE_ZITADEL_CLIENT_ID` (default `runefoble-api`).
- `RUNEFOBLE_ZITADEL_INTERNAL_URL` (`zitadel_internal_url`): optional. If set, discovery and JWKS requests go to this origin with `Host` set to the issuer host. If empty, the verifier reads discovery from the issuer.

There is no development mode and no environment flag that skips verification. The settings are defined in `libs/runefoble_platform/src/runefoble_platform/config.py`.

## TypeScript Services

The TypeScript `audience_studio` service follows the same contract. It has no Python runtime, so it uses `jose` (`services/audience_studio/src/identity/`):
- `ZitadelAuthService` checks RS256 only, `iss`, `aud`, `exp`, and `sub`. It reads `jwks_uri` from OIDC discovery, through `RUNEFOBLE_ZITADEL_INTERNAL_URL` when that setting is set.
- `registerIdentityHook` runs before every route except `/healthz`, `/readyz`, and `/ui/manifest`. It reads the bearer header for HTTP and the `runefoble.bearer.<jwt>` subprotocol for WebSockets. It refuses a handshake before accept.
- A rejected token returns `401`. A JWKS fetch failure returns `503`. The service never reads identity from headers or the body.
- The service refuses to start when `RUNEFOBLE_ZITADEL_ISSUER` or `RUNEFOBLE_ZITADEL_AUDIENCE` is unset.

## See Also
- [Authenticate Users with Zitadel OIDC and JWTs](authenticate-with-zitadel-oidc.md)
- [Define SpiceDB Zanzibar Permissions](define-spicedb-zanzibar-permissions.md)
