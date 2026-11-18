"""Session real-time WebSocket: admit, authorize `session.observe`, then relay per session."""

from __future__ import annotations

import logging

from fastapi import WebSocket, WebSocketDisconnect
from gateway_api.dependencies import WebSocketConnectionManager, ws_manager
from gateway_api.session_access import socket_may
from gateway_api.websocket_auth import admit_gateway_websocket

logger = logging.getLogger("runefoble.gateway.session_websocket")


async def session_websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    manager: WebSocketConnectionManager = ws_manager,
) -> None:
    """Realtime stream connecting board, voice, and Watcher chronicle for one session."""
    principal = await admit_gateway_websocket(websocket)
    if principal is None:
        return
    if not await socket_may(websocket, session_id, principal.user_id, "observe"):
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
