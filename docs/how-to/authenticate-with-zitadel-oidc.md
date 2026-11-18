# How-To: Authenticate Users with Zitadel OIDC and JWTs

## Overview
Runefoble integrates with self-hosted Zitadel (`ghcr.io/zitadel/zitadel`) for OIDC sign-in. Zitadel issues RS256 access tokens. The `sub` claim is the user ID. The platform uses this ID as the Zanzibar `subject_id` in SpiceDB.

The platform has one identity verifier: `ZitadelAuthService` in `libs/runefoble_auth`. No mode disables verification. No header, query parameter, or request body sets identity. Roles and admin flags are not identity. Authorization comes from SpiceDB only (ADR-0001).

## Architecture & Verification Flows

1. **User Login**: The frontend signs the user in with Zitadel (PKCE flow).
2. **Token Issuance**: Zitadel issues an RS256 access token with `sub`, `iss`, `aud`, `exp`, and optional `email` and `preferred_username`.
3. **Verification**: `ZitadelAuthService.verify_token` checks the RS256 signature against the issuer's JWKS. It checks `exp`, `sub`, `iss` (exact match), and `aud` (exact match). Any failure raises `TokenVerificationError`.
4. **Principal**: A passing token yields a `VerifiedPrincipal` (`user_id`, `username`, `email`).
5. **Zanzibar Check**: The `user_id` is the SpiceDB subject for permission checks.

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant GW as Gateway API
    participant ZS as ZitadelAuthService
    participant JWKS as Zitadel JWKS Endpoint
    participant SP as SpiceDB Zanzibar

    Client->>GW: GET /api/v1/sessions/c1 (Bearer Token)
    GW->>ZS: verify_token(token)
    opt JWKS Cache Miss or Expired
        ZS->>JWKS: GET jwks_uri (from OIDC discovery)
        JWKS-->>ZS: JWK Set (keys)
    end
    ZS-->>GW: VerifiedPrincipal(user_id="alice")
    GW->>SP: check_permission(campaign:c1, view, user:alice)
    SP-->>GW: allowed=true
    GW-->>Client: 200 OK (Session State)
```

---

## Step 1: Verify Tokens in `ZitadelAuthService`

```python
from runefoble_auth.principal import VerifiedPrincipal
from runefoble_auth.zitadel import ZitadelAuthService

auth_service = ZitadelAuthService(
    issuer="http://zitadel:8080",  # Must equal the token `iss` claim
    audience="runefoble-api",  # Must equal the token `aud` claim
    jwks_url=None,  # None: read jwks_uri from OIDC discovery
    jwks_cache_ttl=300,  # Seconds
)

principal: VerifiedPrincipal = auth_service.verify_token(bearer_token)
```

Rules:
- `verify_token` accepts only `RS256`.
- `jwks_url` defaults to the `jwks_uri` in `<issuer>/.well-known/openid-configuration`. Zitadel does not serve keys at `/.well-known/jwks.json`.
- Settings: `zitadel_issuer`, `zitadel_audience` (defaults to `zitadel_client_id`), and `zitadel_jwks_url` (optional internal URL for key fetch).
- There is no offline or development bypass. Tests mint real signed tokens (Step 5).

---

## Step 2: Enforce Authentication in Gateway HTTP Endpoints

Use the shared dependency. Do not write a new one.

```python
from typing import Annotated

from fastapi import APIRouter, Depends
from gateway_api.auth import get_current_user, require_zanzibar_permission
from runefoble_auth.principal import VerifiedPrincipal

router = APIRouter()


@router.get("/api/v1/profile")
async def get_profile(user: Annotated[VerifiedPrincipal, Depends(get_current_user)]):
    return {"user_id": user.user_id, "username": user.username, "email": user.email}


@router.get(
    "/api/v1/sessions/{session_id}",
    dependencies=[Depends(require_zanzibar_permission("view", resource_type="campaign"))],
)
async def get_session(session_id: str):
    return {"id": session_id, "status": "active"}
```

A missing, malformed, or unverified Bearer token returns `HTTP 401` with `WWW-Authenticate: Bearer`. For the full contract, see [Verify Identity in FastAPI and WebSockets](verify-identity-in-fastapi-and-websockets.md).

The gateway does not read an `X-User-Id` header as identity. Use the verified token subject. Public routes are limited to health checks, OpenAPI and docs pages, the sign-in flow, and the spectator view. Upload and delete routes for assets take the owner from the token.

---

## Step 3: Authenticate Real-Time WebSocket Handshakes

Browsers cannot set `Authorization` on a WebSocket. The client offers two subprotocols:

1. `runefoble.v1` (the protocol name)
2. `runefoble.bearer.<jwt>` (the token)

The server reads the bearer subprotocol, verifies the token, and rejects the handshake before accept on failure. On success it accepts with `runefoble.v1`. Tokens in the URL query string are not accepted by the shared helper.

```python
from fastapi import WebSocket
from runefoble_auth.websocket import admit_websocket


async def campaign_websocket_endpoint(websocket: WebSocket, verifier) -> None:
    principal = await admit_websocket(websocket, verifier)
    if principal is None:
        return  # Refused with close code 1008 before accept
    # Verify SpiceDB permissions for principal.user_id before serving the session.
```

Every gateway WebSocket route calls `admit_websocket` before accept (TASK-0522). Tokens in the query string are refused.

---

## Step 4: Frontend Client Authentication

The App Shell uses the OIDC authorization-code flow with PKCE (ADR-0015 d). The App Shell never reads a password. Its code lives in `frontend/src/auth/`.

1. **Runtime settings.** The App Shell loads `/runtime-config.json`. It holds the issuer, client ID, scopes, and provider name. Helm renders the file. The client ID is empty until the identity bootstrap sets it. Sign-in fails with a clear message until then.
2. **Sign-in.** `authService.startSignIn()` creates a `code_verifier`, its S256 `code_challenge`, a `state`, and a `nonce`. It keeps the verifier, state, and nonce in `sessionStorage`. It then sends the browser to the Zitadel authorize endpoint. Discovery at `<issuer>/.well-known/openid-configuration` supplies the endpoints. `Create Account` adds `prompt=create`, which opens the hosted sign-up page.
3. **Callback.** Zitadel redirects to `/auth/callback?code=...&state=...`. The App Shell checks `state` and the ID token `nonce`, exchanges the code with the verifier, and stores the tokens. It removes the code and state from the URL. Any error clears the session and shows the reason on the sign-in gate. A redirect URI cannot carry a fragment, so this callback is a real path, not a `#/` route.
4. **Renewal.** The App Shell renews the access token with the `refresh_token` grant. The scope list includes `offline_access`. A rejected refresh clears the session and returns the user to sign-in.
5. **Logout.** The App Shell clears local tokens and redirects to the Zitadel end-session endpoint with `id_token_hint`.

The App Shell sends the access token as `Authorization: Bearer`. The guard treats a token as present only while its own `exp` is in the future. Roles in the token are display data only. Permissions come from SpiceDB through the gateway (Hard Invariant 1).

---

## Step 5: Test with Signed Tokens

Tests use `SigningTestIssuer` from `runefoble_auth.testing.signing_test_issuer`. It creates an RSA key, mints RS256 tokens, and builds a verifier that trusts only that key.

```python
from runefoble_auth.testing.signing_test_issuer import SigningTestIssuer

issuer = SigningTestIssuer()
verifier = issuer.verifier()
token = issuer.mint("user-evelyn", username="evelyn")
```

Use `mint(..., expires_in=-60)`, `mint(..., audience="other")`, or `mint(..., issuer="http://evil.test")` for negative tests. Forge tokens with another key or with HS256 or `alg: none` to test rejection.

Shared fixtures are in `tests/helpers/zitadel_auth.py`. The `auth_environment` fixture configures the gateway with a signing verifier.

---

## Service-to-Service Credentials

A service that calls another service presents a service credential, not a user token (ADR-0015 e). The credential is a shared secret. It is stored in a Kubernetes Secret and mounted into the calling pod.

The Zitadel machine-user client credentials flow is the alternative. This platform does not use it yet.

### Current use: The Watcher to the inference worker

| Setting | Read by | Meaning |
|---|---|---|
| `RUNEFOBLE_INFERENCE_SERVICE_TOKEN` | `inference_worker`, `the_watcher` | Bearer credential. No default value. |

Rules:
- The inference worker requires `Authorization: Bearer <token>` on every `/inference/v1/*` route. It compares the value with `hmac.compare_digest`. Any other caller gets `401` with `WWW-Authenticate: Bearer`.
- The inference worker refuses to start when the setting is unset or blank.
- The inference worker sends no CORS headers. Browsers cannot call it.
- The Watcher sends the token on every worker call. When the setting is unset, The Watcher returns `503 backend_unavailable` and makes no call.
- A Zitadel user token is not a service credential. The inference worker returns `401` for it.

### Helm

The chart does not create the Secret. It references the Secret in `deployments/helm/runefoble/values.yaml`:

```yaml
inferenceServiceToken:
  secretName: runefoble-inference-service
  key: token
```

Create the Secret before you install the chart:

```bash
kubectl create secret generic runefoble-inference-service \
  --from-literal=token="$(openssl rand -hex 32)"
```

Both the `inference-worker` and `the-watcher` deployments read the key as `RUNEFOBLE_INFERENCE_SERVICE_TOKEN`.

### Test with a service credential

Set the same value in the test process and mint no user token for the worker. The root `tests/conftest.py` sets `RUNEFOBLE_INFERENCE_SERVICE_TOKEN=test-only-inference-token` before any settings load. Send the header from the test client:

```python
from httpx import ASGITransport, AsyncClient
from inference_worker import api

headers = {"Authorization": "Bearer test-only-inference-token"}
async with AsyncClient(transport=ASGITransport(app=api.app), base_url="http://test", headers=headers) as ac:
    res = await ac.post("/inference/v1/intent", json=payload)
```

Tests for the refusal paths are in `tests/test_blackbox_service_identity.py`.

---

## Verification & Blackbox Testing

- **Principal and HTTP dependency**: `libs/runefoble_auth/tests/test_verified_principal.py` covers accepted tokens and rejected tokens (missing, garbage, HS256, `alg: none`, unsigned, unknown key, expired, wrong `aud`, wrong `iss`, missing or empty `sub`) and the WebSocket handshake.
- **HTTP Bearer & JWKS (gateway)**: `tests/test_blackbox_zitadel_http_auth.py`.
- **WebSocket handshake (gateway)**: `tests/test_blackbox_zitadel_websocket_auth.py`.
- **Shared Auth Fixtures**: `tests/helpers/zitadel_auth.py`.
- **game_session, The Watcher, and inference worker identity**: `tests/test_blackbox_service_identity.py`.
