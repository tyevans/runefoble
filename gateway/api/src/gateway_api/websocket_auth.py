"""Gateway WebSocket admission. Binds the gateway verifier to the shared handshake check."""

from __future__ import annotations

from fastapi import WebSocket
from gateway_api.auth import get_zitadel_auth_service
from runefoble_auth.principal import BearerVerifier, VerifiedPrincipal
from runefoble_auth.websocket import WebSocketAuthorizer, admit_websocket


async def admit_gateway_websocket(
    websocket: WebSocket,
    authorize: WebSocketAuthorizer | None = None,
    *,
    verifier: BearerVerifier | None = None,
    denial_message: str | None = None,
) -> VerifiedPrincipal | None:
    """Admit a gateway WebSocket. Return None when the handshake or the permission is refused."""
    return await admit_websocket(
        websocket,
        verifier or get_zitadel_auth_service(),
        authorize,
        denial_message=denial_message,
    )


__all__ = ["admit_gateway_websocket"]
