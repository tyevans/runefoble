"""Authentication and credential extraction helpers for campaign WebSockets."""

from __future__ import annotations

import logging

from fastapi import HTTPException, WebSocket
from runefoble_auth.zitadel import ZitadelAuthService

logger = logging.getLogger("runefoble.gateway.websocket_auth")


def extract_token_from_websocket(websocket: WebSocket) -> str | None:
    """Extract JWT token from WebSocket query parameters or headers."""
    token = websocket.query_params.get("token") or websocket.query_params.get("access_token")
    if token:
        return token
    auth = websocket.headers.get("authorization")
    if auth and auth.startswith("Bearer "):
        return auth[7:].strip()
    protocols = websocket.headers.get("sec-websocket-protocol")
    if protocols:
        for proto in protocols.split(","):
            p = proto.strip()
            if p.startswith("bearer."):
                return p[7:]
    return None


def extract_subject_id(websocket: WebSocket) -> str:
    """Extract authenticated subject identifier from WebSocket query or headers (dev mode)."""
    for param in ("user_id", "x_user_id", "subject_id"):
        val = websocket.query_params.get(param)
        if val:
            return val
    x_user = websocket.headers.get("x-user-id")
    if x_user:
        return x_user
    return "guest"


def authenticate_websocket(
    websocket: WebSocket,
    service: ZitadelAuthService,
) -> str:
    """Authenticate incoming WebSocket connection, returning the authenticated subject ID."""
    token = extract_token_from_websocket(websocket)
    if token:
        try:
            user = service.verify_token(token)
            return user.user_id
        except Exception as exc:
            logger.warning("WebSocket token verification failed: %s", exc)
            raise HTTPException(
                status_code=401,
                detail=f"Token verification failed: {exc}",
            ) from exc

    if service.dev_mode:
        return extract_subject_id(websocket)

    logger.warning("WebSocket connection rejected: missing token in production mode")
    raise HTTPException(
        status_code=401,
        detail="Authentication required: missing token",
    )


__all__ = [
    "authenticate_websocket",
    "extract_subject_id",
    "extract_token_from_websocket",
    "logger",
]
