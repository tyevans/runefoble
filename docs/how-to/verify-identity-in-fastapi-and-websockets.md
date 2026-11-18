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

verifier = ZitadelAuthService(issuer="http://zitadel:8080", audience="runefoble-api")
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

`admit_websocket` verifies the handshake. On success it accepts with `runefoble.v1`. On failure it closes with code 1008 before accept, logs the path and the reason (never the token), and returns `None`.

Rules:
- Call `admit_websocket` first. Do not accept the socket in the route before it.
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
- `RUNEFOBLE_ZITADEL_AUDIENCE` (`zitadel_audience`): must equal the token `aud`. Defaults to `RUNEFOBLE_ZITADEL_CLIENT_ID`.
- `RUNEFOBLE_ZITADEL_JWKS_URL` (`zitadel_jwks_url`): optional. If empty, the verifier reads `jwks_uri` from OIDC discovery.

There is no development mode and no environment flag that skips verification.

## TypeScript Services

The TypeScript `audience_studio` service follows the same contract. It has no Python runtime, so it uses `jose` (`services/audience_studio/src/identity/`):
- `ZitadelVerifier` checks RS256 only, `iss`, `aud`, `exp`, and `sub`. It reads `RUNEFOBLE_ZITADEL_JWKS_URL`, or `jwks_uri` from OIDC discovery when the URL is unset.
- `registerIdentityHook` runs before every route except `/healthz`, `/readyz`, and `/ui/manifest`. It reads the bearer header for HTTP and the `runefoble.bearer.<jwt>` subprotocol for WebSockets. It refuses a handshake before accept.
- A rejected token returns `401`. A JWKS fetch failure returns `503`. The service never reads identity from headers or the body.
- The service refuses to start when `RUNEFOBLE_ZITADEL_ISSUER` or `RUNEFOBLE_ZITADEL_AUDIENCE` is unset.

## See Also
- [Authenticate Users with Zitadel OIDC and JWTs](authenticate-with-zitadel-oidc.md)
- [Define SpiceDB Zanzibar Permissions](define-spicedb-zanzibar-permissions.md)
