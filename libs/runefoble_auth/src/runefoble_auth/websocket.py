"""WebSocket handshake authentication and admission for verified principals.

Browsers cannot set the Authorization header on a WebSocket. The client
offers two subprotocols: the Runefoble protocol and a bearer protocol
that carries the token (`runefoble.bearer.<jwt>`). Tokens in the URL
query string are never accepted.

Use `admit_websocket` in every WebSocket route. It verifies the bearer,
checks the caller's permission when the route needs one, and accepts the
handshake only when both pass. Close codes follow ports-and-endpoints.md:

- 1008: the token is missing or invalid (closed before accept).
- 4403: the token is valid, but the caller lacks the permission.
- 1011: SpiceDB could not answer. A failed check is never a denial.

Use `send_socket_error` for every per-message error frame. Its shape is
`{"type": "error", "code": ..., "message": ..., ...}`.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import WebSocket

from runefoble_auth.contract import permission_for_action
from runefoble_auth.errors import AuthzError
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.principal import BearerVerifier, TokenVerificationError, VerifiedPrincipal

logger = logging.getLogger("runefoble.auth.websocket")

RUNEFOBLE_SUBPROTOCOL = "runefoble.v1"
BEARER_SUBPROTOCOL_PREFIX = "runefoble.bearer."
WS_POLICY_VIOLATION = 1008
WS_AUTHORIZATION_REFUSED = 4403
WS_AUTHORIZATION_UNAVAILABLE = 1011

WebSocketAuthorizer = Callable[[str], Awaitable[bool]]
"""Return True when the user id may open the socket. May raise AuthzError."""


class WebSocketAuthError(Exception):
    """Raised when the WebSocket handshake carries no valid bearer subprotocol."""


def bearer_token_from_subprotocols(offered: list[str]) -> str | None:
    """Return the token carried by the first `runefoble.bearer.<jwt>` protocol."""
    for protocol in offered:
        if protocol.startswith(BEARER_SUBPROTOCOL_PREFIX):
            token = protocol[len(BEARER_SUBPROTOCOL_PREFIX) :]
            if token:
                return token
    return None


def authenticate_websocket(websocket: WebSocket, verifier: BearerVerifier) -> VerifiedPrincipal:
    """Verify the bearer subprotocol offered in the handshake."""
    offered: list[str] = list(websocket.scope.get("subprotocols", []))
    token = bearer_token_from_subprotocols(offered)
    if token is None:
        raise WebSocketAuthError("Missing bearer subprotocol")
    try:
        return verifier.verify_token(token)
    except TokenVerificationError as exc:
        raise WebSocketAuthError("Token verification failed") from exc


async def verify_websocket(
    websocket: WebSocket, verifier: BearerVerifier
) -> VerifiedPrincipal | None:
    """Verify the handshake without accepting it. On failure, close with 1008 and return None.

    Use this only when the route must choose its own subprotocol at accept time.
    """
    try:
        return authenticate_websocket(websocket, verifier)
    except WebSocketAuthError as exc:
        logger.warning("WebSocket handshake denied on %s: %s", websocket.url.path, exc)
        await websocket.close(code=WS_POLICY_VIOLATION)
        return None


def action_authorizer(action: str, resource_id: str) -> WebSocketAuthorizer:
    """Build the check for a domain action on one object (ADR-0001, `runefoble.zed`)."""
    resource_type, permission = permission_for_action(action)

    async def _check(user_id: str) -> bool:
        return await get_spicedb_client().check_permission(
            resource_type, resource_id, permission, "user", user_id
        )

    return _check


async def admit_websocket(
    websocket: WebSocket,
    verifier: BearerVerifier,
    authorize: WebSocketAuthorizer | None = None,
    *,
    denial_message: str | None = None,
) -> VerifiedPrincipal | None:
    """Verify the handshake and the optional permission, then accept with the Runefoble subprotocol.

    A refused handshake returns None, and the caller must return at once. Refusals:

    - Invalid or missing token: 1008 before accept.
    - Permission refused: 4403 before accept. When `denial_message` is set, the socket
      accepts first, sends a `PERMISSION_DENIED` frame with that message, then closes 4403.
    - SpiceDB failure: 1011 before accept.

    The log names only the path and the outcome. It never names the token.
    """
    principal = await verify_websocket(websocket, verifier)
    if principal is None:
        return None
    if authorize is not None:
        try:
            allowed = await authorize(principal.user_id)
        except AuthzError:
            logger.error("WebSocket authorization unavailable on %s", websocket.url.path)
            await websocket.close(
                code=WS_AUTHORIZATION_UNAVAILABLE, reason="Authorization unavailable"
            )
            return None
        if not allowed:
            logger.warning("WebSocket refused on %s: permission denied", websocket.url.path)
            if denial_message is None:
                await websocket.close(code=WS_AUTHORIZATION_REFUSED, reason="Forbidden")
                return None
            await websocket.accept(subprotocol=RUNEFOBLE_SUBPROTOCOL)
            await send_socket_error(
                websocket, "PERMISSION_DENIED", denial_message, action="connect"
            )
            await websocket.close(code=WS_AUTHORIZATION_REFUSED, reason="Forbidden")
            return None
    await websocket.accept(subprotocol=RUNEFOBLE_SUBPROTOCOL)
    return principal


async def send_socket_error(websocket: WebSocket, code: str, message: str, **fields: Any) -> None:
    """Send one per-message error frame. Extra fields (for example `action`) join the frame."""
    await websocket.send_json({"type": "error", "code": code, "message": message, **fields})


__all__ = [
    "BEARER_SUBPROTOCOL_PREFIX",
    "RUNEFOBLE_SUBPROTOCOL",
    "WS_AUTHORIZATION_REFUSED",
    "WS_AUTHORIZATION_UNAVAILABLE",
    "WS_POLICY_VIOLATION",
    "WebSocketAuthError",
    "WebSocketAuthorizer",
    "action_authorizer",
    "admit_websocket",
    "authenticate_websocket",
    "bearer_token_from_subprotocols",
    "send_socket_error",
    "verify_websocket",
]
