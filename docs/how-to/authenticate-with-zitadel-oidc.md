# How-To: Authenticate Users with Zitadel OIDC and JWTs

## Overview
Runefoble integrates with self-hosted Zitadel (`ghcr.io/zitadel/zitadel`) to provide OIDC identity management, user authentication, and project role mapping. Authenticated user IDs extracted from Zitadel JWTs serve directly as Zanzibar `subject_id` identifiers in SpiceDB.

## Architecture & Flows

1. **User Login**: The frontend client redirects to Zitadel (`/auth`) via PKCE flow.
2. **Token Issuance**: Zitadel issues an RS256-signed JWT containing `sub` (User ID), `email`, and project roles.
3. **Gateway Verification**: `gateway-api` retrieves Zitadel's public keys from `http://zitadel:8080/oauth/v2/keys` (JWKS), validates token signatures, and checks expiration.
4. **Zanzibar Check**: The verified `user_id` is passed to SpiceDB client dependencies to verify permissions.

---

## Step 1: Decode & Verify Token in `ZitadelAuthService`

Use `ZitadelAuthService` from `libs/runefoble_auth`:

```python
from runefoble_auth.zitadel import ZitadelAuthService, AuthenticatedUser

# Initialize service pointing to internal Zitadel issuer
auth_service = ZitadelAuthService(
    issuer="http://zitadel:8080",
    client_id="runefoble-api",
)

# Decode and verify token signature against JWKS
user: AuthenticatedUser = auth_service.decode_token(bearer_token, verify=True)
print(f"Authenticated user: {user.username} ({user.user_id})")
print(f"Assigned roles: {user.roles}")
```

In local unit tests where Zitadel is not running, set `verify=False` or export `RUNEFOBLE_AUTH_DEV_MODE=true` to allow fallback test user contexts (`dev-user-001`).

---

## Step 2: Enforce Authentication in Gateway Endpoints

FastAPI endpoints inject authenticated user context via dependencies:

```python
from fastapi import APIRouter, Depends, Header, HTTPException
from runefoble_auth.zitadel import AuthenticatedUser, ZitadelAuthService

router = APIRouter()
auth_service = ZitadelAuthService()


async def get_current_user(authorization: str | None = Header(None)) -> AuthenticatedUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Bearer token")

    token = authorization.split(" ")[1]
    try:
        return auth_service.decode_token(token, verify=True)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Token verification failed: {exc}")


@router.get("/api/v1/profile")
async def get_profile(user: AuthenticatedUser = Depends(get_current_user)):
    return {
        "user_id": user.user_id,
        "username": user.username,
        "roles": user.roles,
    }
```

---

## Step 3: Authenticate WebSocket Handshakes

For real-time connections (`/ws/campaigns/{campaign_id}`), clients send the token as a query parameter or `Sec-WebSocket-Protocol` header:

```python
from fastapi import WebSocket, WebSocketDisconnect
from runefoble_auth.zitadel import ZitadelAuthService


async def campaign_websocket_endpoint(websocket: WebSocket, campaign_id: str):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401, reason="Authentication token required")
        return

    try:
        user = auth_service.decode_token(token, verify=True)
    except Exception:
        await websocket.close(code=4403, reason="Invalid token signature")
        return

    await websocket.accept()
    # Proceed to SpiceDB permission checks with user.user_id
```
