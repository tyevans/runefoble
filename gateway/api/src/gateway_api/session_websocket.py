"""Session real-time WebSocket: admit, authorize `session.observe`, then relay per session.

Observers receive frames. Inbound frames need `session.participate` (TASK-0810). Each inbound
frame is validated against the session frame contract before the permission check.
"""

from __future__ import annotations

import logging

from fastapi import WebSocket, WebSocketDisconnect
from gateway_api.dependencies import WebSocketConnectionManager, ws_manager
from gateway_api.session_access import may_publish_frame
from gateway_api.session_frames import InboundFrameError, read_session_frame
from gateway_api.websocket_auth import admit_gateway_websocket
from runefoble_auth.websocket import action_authorizer, send_socket_error

logger = logging.getLogger("runefoble.gateway.session_websocket")


async def session_websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    manager: WebSocketConnectionManager = ws_manager,
) -> None:
    """Realtime stream connecting board, voice, and Watcher chronicle for one session."""
    principal = await admit_gateway_websocket(
        websocket, action_authorizer("session.observe", session_id)
    )
    if principal is None:
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
            text = await websocket.receive_text()
            try:
                kind, payload = read_session_frame(text)
            except InboundFrameError as exc:
                await send_socket_error(websocket, exc.code, exc.message)
                continue
            if not await may_publish_frame(websocket, session_id, principal.user_id, kind):
                continue
            await manager.broadcast(session_id, payload)
    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket)


__all__ = ["session_websocket_endpoint"]
