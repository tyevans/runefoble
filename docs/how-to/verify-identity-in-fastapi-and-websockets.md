# How-To: Verify Identity in FastAPI and WebSockets

## Purpose
Use this guide to protect a FastAPI HTTP route or WebSocket with a verified principal. The shared helpers live in `libs/runefoble_auth`. Every bounded context uses them. Do not write a new token parser.

## The Contract
- A **verified principal** is `VerifiedPrincipal(user_id, username, email)`.
- It has no roles and no admin flag. Roles are not authority. Use SpiceDB checks for permissions (ADR-0001).
- A request has identity only when its bearer token passes `ZitadelAuthService.verify_token`.
- Every failure raises a 401 (HTTP) or closes the handshake before accept (WebSocket). There is no fallback identity.

## HTTP: Use `require_principal`

`require_principal` builds a FastAPI dependency. It reads only `Authorization: Bearer <token>`.

```python
from typing import Annotated

from fastapi import Depends, FastAPI
from runefoble_auth.principal import VerifiedPrincipal, require_principal
from runefoble_auth.zitadel import ZitadelAuthService

verifier = ZitadelAuthService(
    issuer="http://auth.localhost",  # Must equal the token `iss` claim
    audience="364509876543210987",  # The project ID in a cluster
    internal_url="http://zitadel:8080",  # In-cluster origin. Requests carry Host: auth.localhost
)
get_principal = require_principal(lambda: verifier)

app = FastAPI()


@app.get("/api/v1/example")
def example(principal: Annotated[VerifiedPrincipal, Depends(get_principal)]):
    return {"user_id": principal.user_id}
```

Behavior:
- Missing header, a non-Bearer scheme, an empty token, or any verification failure returns `401` with body `{"error": "unauthorized", "message": ...}` and header `WWW-Authenticate: Bearer`.
- On success the dependency sets `request.state.principal`.
- The dependency is synchronous. FastAPI runs it in a worker thread, so a JWKS fetch does not block the event loop.

Gateway code uses the same pattern through `gateway_api.auth.get_current_user`.

## Routers: Depend on the Router and Take a `CallerId`

Bounded contexts that serve many routes apply the principal dependency at router level. This protects every route in the router, including routes that do not read identity.

```python
from typing import Annotated

from fastapi import APIRouter, Depends
from game_session.settlement.auth.tokens import CallerId, get_caller_principal

router = APIRouter(dependencies=[Depends(get_caller_principal)])


@router.post("/api/v1/example/{item_id}")
async def act(item_id: str, caller_id: CallerId):
    return {"acting_user": caller_id, "item": item_id}
```

- `CallerId` is the verified token subject as a string. Use it for every permission check.
- Do not add a query, header, or body field for identity. A forged value never reaches the route.
- Keep public routes (health, manifests, OpenAPI) on the app, not on a guarded router.
- WebSocket routes do not use `require_principal`. They call `admit_websocket` (below).
- The Watcher uses the same names from `the_watcher.identity`.

## Routes That Another Service Calls: Accept the Service Credential

Use `require_user_or_service_credential` only on a route that another service calls and that does not act for a user. The MCP gateway calls such routes. The dependency accepts either:

- a verified user bearer in `Authorization`, which gives `CallerIdentity(user_id=<subject>)`; or
- the service credential in `X-Runefoble-Service-Credential`, which gives `CallerIdentity(user_id=None)`.

```python
from runefoble_auth.caller import CallerIdentity, require_user_or_service_credential
from runefoble_platform.service_credential import expected_service_credential

SERVICE_CREDENTIAL = expected_service_credential()  # refuses start-up when unset
get_caller_or_service = require_user_or_service_credential(get_verifier, SERVICE_CREDENTIAL)


@router.get("/api/v1/things/{thing_id}", dependencies=[Depends(get_caller_or_service)])
async def read_thing(thing_id: UUID): ...
```

Rules:
- A route with a user-scoped permission check keeps `require_principal` or a `CallerId`. A service call must never reach it.
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

## Test Both Paths With Signed Tokens

```python
from runefoble_auth.testing.signing_test_issuer import SigningTestIssuer

issuer = SigningTestIssuer()
verifier = issuer.verifier()
token = issuer.mint("user-evelyn")
client.get("/api/v1/example", headers={"Authorization": f"Bearer {token}"})
client.websocket_connect("/ws", subprotocols=["runefoble.v1", f"runefoble.bearer.{token}"])
```

Negative cases to cover: no token, garbage, HS256 with a known secret, `alg: none`, unsigned, unknown key, expired, wrong `aud`, wrong `iss`, missing `sub`. The reference suite is `libs/runefoble_auth/tests/test_verified_principal.py`.

## Configuration
- `RUNEFOBLE_ZITADEL_ISSUER` (`zitadel_issuer`): must equal the token `iss`.
- `RUNEFOBLE_ZITADEL_AUDIENCE` (`zitadel_audience`): must equal the token `aud`. In a cluster it is the project ID from the Secret `runefoble-zitadel-client`.
- `RUNEFOBLE_ZITADEL_INTERNAL_URL` (`zitadel_internal_url`): optional. If set, discovery and JWKS requests go to this origin with `Host` set to the issuer host. If empty, the verifier reads discovery from the issuer.

There is no development mode and no environment flag that skips verification.

## TypeScript Services

The TypeScript `audience_studio` service follows the same contract. It has no Python runtime, so it uses `jose` (`services/audience_studio/src/identity/`):
- `ZitadelAuthService` checks RS256 only, `iss`, `aud`, `exp`, and `sub`. It reads `jwks_uri` from OIDC discovery, through `RUNEFOBLE_ZITADEL_INTERNAL_URL` when that setting is set.
- `registerIdentityHook` runs before every route except `/healthz`, `/readyz`, and `/ui/manifest`. It reads the bearer header for HTTP and the `runefoble.bearer.<jwt>` subprotocol for WebSockets. It refuses a handshake before accept.
- A rejected token returns `401`. A JWKS fetch failure returns `503`. The service never reads identity from headers or the body.
- The service refuses to start when `RUNEFOBLE_ZITADEL_ISSUER` or `RUNEFOBLE_ZITADEL_AUDIENCE` is unset.

## See Also
- [Authenticate Users with Zitadel OIDC and JWTs](authenticate-with-zitadel-oidc.md)
- [Define SpiceDB Zanzibar Permissions](define-spicedb-zanzibar-permissions.md)
