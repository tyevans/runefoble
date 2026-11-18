"""Session real-time WebSocket: admit, authorize `session.observe`, then relay per session."""

from __future__ import annotations

import logging

from fastapi import WebSocket, WebSocketDisconnect
from gateway_api.auth import get_spicedb_client
from gateway_api.dependencies import WebSocketConnectionManager, ws_manager
from gateway_api.websocket_auth import admit_gateway_websocket
from runefoble_auth.errors import AuthzUnavailableError

logger = logging.getLogger("runefoble.gateway.session_websocket")

FORBIDDEN_CLOSE_CODE = 4403
UNAVAILABLE_CLOSE_CODE = 1011


async def _may_observe(websocket: WebSocket, session_id: str, user_id: str) -> bool:
    """Check `session.observe`. Close the socket and return False when it is not allowed."""
    try:
        allowed = await get_spicedb_client().check_permission(
            resource_type="session",
            resource_id=session_id,
            permission="observe",
            subject_type="user",
            subject_id=user_id,
        )
    except AuthzUnavailableError:
        logger.error("Authorization unavailable for session socket on '%s'", session_id)
        await websocket.close(code=UNAVAILABLE_CLOSE_CODE, reason="Authorization unavailable")
        return False
    if not allowed:
        logger.warning("Session socket refused: '%s' cannot observe '%s'", user_id, session_id)
        await websocket.close(code=FORBIDDEN_CLOSE_CODE, reason="Forbidden: cannot observe session")
        return False
    return True


async def session_websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    manager: WebSocketConnectionManager = ws_manager,
) -> None:
    """Realtime stream connecting board, voice, and Watcher chronicle for one session."""
    principal = await admit_gateway_websocket(websocket)
    if principal is None:
        return
    if not await _may_observe(websocket, session_id, principal.user_id):
        return
    manager.register(session_id, websocket)
    try:
        await websocket.send_json(
            {
                "type": "connected",
                "session_id": session_id,
                "message": "Connected to Runefoble real-time stream. The Watcher is listening.",
            }
        )
        while True:
            data = await websocket.receive_json()
            await manager.broadcast(session_id, data)
    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket)


__all__ = ["session_websocket_endpoint"]
