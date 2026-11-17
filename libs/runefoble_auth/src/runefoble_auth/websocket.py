"""WebSocket handshake authentication for verified principals.

Browsers cannot set the Authorization header on a WebSocket. The client
offers two subprotocols: the Runefoble protocol and a bearer protocol
that carries the token (`runefoble.bearer.<jwt>`). Tokens in the URL
query string are never accepted.

Use `admit_websocket` in every WebSocket route. It verifies the handshake
and accepts it, or closes it before accept. No route accepts first.
"""

from __future__ import annotations

import logging

from fastapi import WebSocket

from runefoble_auth.principal import BearerVerifier, TokenVerificationError, VerifiedPrincipal

logger = logging.getLogger("runefoble.auth.websocket")

RUNEFOBLE_SUBPROTOCOL = "runefoble.v1"
BEARER_SUBPROTOCOL_PREFIX = "runefoble.bearer."
WS_POLICY_VIOLATION = 1008


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


async def admit_websocket(
    websocket: WebSocket, verifier: BearerVerifier
) -> VerifiedPrincipal | None:
    """Verify the handshake, then accept it with the Runefoble subprotocol.

    On failure, close the handshake before accept, log only the path and
    the reason, and return None. The caller must return at once on None.
    """
    try:
        principal = authenticate_websocket(websocket, verifier)
    except WebSocketAuthError as exc:
        logger.warning("WebSocket handshake denied on %s: %s", websocket.url.path, exc)
        await websocket.close(code=WS_POLICY_VIOLATION)
        return None
    await websocket.accept(subprotocol=RUNEFOBLE_SUBPROTOCOL)
    return principal


__all__ = [
    "BEARER_SUBPROTOCOL_PREFIX",
    "RUNEFOBLE_SUBPROTOCOL",
    "WS_POLICY_VIOLATION",
    "WebSocketAuthError",
    "admit_websocket",
    "authenticate_websocket",
    "bearer_token_from_subprotocols",
]
