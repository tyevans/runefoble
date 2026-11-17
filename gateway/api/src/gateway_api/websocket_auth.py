"""Gateway WebSocket admission. Binds the gateway verifier to the shared handshake check."""

from __future__ import annotations

import logging

from fastapi import WebSocket
from gateway_api.auth import get_zitadel_auth_service
from runefoble_auth.principal import BearerVerifier, VerifiedPrincipal
from runefoble_auth.websocket import admit_websocket

logger = logging.getLogger("runefoble.gateway.websocket_auth")


async def admit_gateway_websocket(
    websocket: WebSocket,
    verifier: BearerVerifier | None = None,
) -> VerifiedPrincipal | None:
    """Admit a gateway WebSocket before accept. Return None when the handshake is refused."""
    return await admit_websocket(websocket, verifier or get_zitadel_auth_service())


__all__ = ["admit_gateway_websocket"]
