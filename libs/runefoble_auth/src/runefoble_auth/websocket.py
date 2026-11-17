"""WebSocket handshake authentication for verified principals.

Browsers cannot set the Authorization header on a WebSocket. The client
offers two subprotocols: the Runefoble protocol and a bearer protocol
that carries the token (`runefoble.bearer.<jwt>`). Tokens in the URL
query string are never accepted.

The caller must reject the handshake before accept when this raises.
On success the caller accepts with `subprotocol=RUNEFOBLE_SUBPROTOCOL`.
"""

from __future__ import annotations

from fastapi import WebSocket

from runefoble_auth.principal import BearerVerifier, TokenVerificationError, VerifiedPrincipal

RUNEFOBLE_SUBPROTOCOL = "runefoble.v1"
BEARER_SUBPROTOCOL_PREFIX = "runefoble.bearer."


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


__all__ = [
    "BEARER_SUBPROTOCOL_PREFIX",
    "RUNEFOBLE_SUBPROTOCOL",
    "WebSocketAuthError",
    "authenticate_websocket",
    "bearer_token_from_subprotocols",
]
