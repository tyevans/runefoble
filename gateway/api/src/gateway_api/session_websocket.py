"""Session real-time WebSocket: admit, authorize `session.observe`, then relay per session.

Observers receive frames. Inbound frames need `session.participate` (TASK-0810). Each inbound
frame is validated against the session frame contract before the permission check.
"""

from __future__ import annotations

import logging

from fastapi import WebSocket
from gateway_api.dependencies import ws_manager
from gateway_api.session_access import may_publish_frame
from gateway_api.session_frames import InboundFrameError, read_session_frame
from gateway_api.websocket_auth import admit_gateway_websocket
from runefoble_auth.principal import VerifiedPrincipal
from runefoble_auth.websocket import action_authorizer, send_socket_error, serve_authorized_socket

logger = logging.getLogger("runefoble.gateway.session_websocket")


async def session_websocket_endpoint(websocket: WebSocket, session_id: str) -> None:
    """Realtime stream connecting board, voice, and Watcher chronicle for one session."""

    async def open_room(principal: VerifiedPrincipal) -> bool:
        ws_manager.register(session_id, websocket)
        await websocket.send_json(
            {
                "type": "connected",
                "session_id": session_id,
                "message": "Connected to Runefoble real-time stream. The Watcher is listening.",
            }
        )
        return True

    async def relay(principal: VerifiedPrincipal, text: str) -> None:
        try:
            kind, payload = read_session_frame(text)
        except InboundFrameError as exc:
            await send_socket_error(websocket, exc.code, exc.message)
            return
        if not await may_publish_frame(websocket, session_id, principal.user_id, kind):
            return
        await ws_manager.broadcast(session_id, payload)

    await serve_authorized_socket(
        websocket,
        admit=lambda ws: admit_gateway_websocket(
            ws, action_authorizer("session.observe", session_id)
        ),
        on_open=open_room,
        on_frame=relay,
        on_close=lambda: ws_manager.disconnect(session_id, websocket),
        receive=WebSocket.receive_text,
    )


__all__ = ["session_websocket_endpoint"]
