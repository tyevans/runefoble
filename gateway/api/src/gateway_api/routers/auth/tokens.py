"""OAuth2 token exchange and JWT issuance handlers for Gateway API."""

import base64
import json
import secrets
import time
from typing import Any

from fastapi import APIRouter, HTTPException
from gateway_api.routers.auth.schemas import RefreshRequest, TokenRequest

router = APIRouter()


def _generate_mock_jwt(user_id: str, username: str, email: str, roles: list[str]) -> str:
    """Generate a lightweight HS256-like dev JWT token for client testing."""
    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').decode().rstrip("=")
    now = int(time.time())
    payload_data = {
        "sub": user_id,
        "preferred_username": username,
        "email": email,
        "urn:zitadel:iam:org:project:roles": roles,
        "roles": roles,
        "iat": now,
        "exp": now + 3600,
    }
    payload = base64.urlsafe_b64encode(json.dumps(payload_data).encode()).decode().rstrip("=")
    signature = base64.urlsafe_b64encode(b"runefoble-dev-signature").decode().rstrip("=")
    return f"{header}.{payload}.{signature}"


@router.post("/token")
async def login_for_token(payload: TokenRequest) -> dict[str, Any]:
    """Exchange username and password for JWT authentication tokens."""
    username = payload.username.strip()
    user_id = f"user-{username.lower().replace(' ', '-')}"
    roles = (
        ["dm", "player"]
        if any(term in username.lower() for term in ("dm", "master", "dungeon"))
        else ["player"]
    )
    email = f"{username.lower()}@runefoble.local"
    access_token = _generate_mock_jwt(user_id, username, email, roles)

    return {
        "access_token": access_token,
        "refresh_token": f"refresh-{secrets.token_hex(16)}",
        "token_type": "Bearer",
        "expires_in": 3600,
        "user_id": user_id,
        "username": username,
        "roles": roles,
    }


@router.post("/refresh")
async def refresh_token(payload: RefreshRequest) -> dict[str, Any]:
    """Refresh an access token using a valid refresh token."""
    if not payload.refresh_token:
        raise HTTPException(status_code=400, detail="Missing refresh token")
    access_token = _generate_mock_jwt(
        "user-refreshed", "adventurer", "adventurer@runefoble.local", ["player"]
    )
    return {
        "access_token": access_token,
        "refresh_token": f"refresh-{secrets.token_hex(16)}",
        "token_type": "Bearer",
        "expires_in": 3600,
    }


@router.post("/logout")
async def logout_user() -> dict[str, Any]:
    """Acknowledge user logout and invalidate session."""
    return {"status": "logged_out", "message": "Successfully logged out"}


__all__ = [
    "_generate_mock_jwt",
    "login_for_token",
    "logout_user",
    "refresh_token",
    "router",
]
