"""Session real-time WebSocket: admit, authorize `session.observe`, then relay per session.

Observers receive frames. At open, the gateway checks `session.control` once and keeps the
answer: a socket of a caller with control joins the DM group, which alone gets DM-only frames
such as `dm_whisper` (TASK-0927). When SpiceDB cannot answer, the socket stays an observer
socket and gets an `AUTHZ_UNAVAILABLE` frame for `dm_whisper`. Each inbound frame is validated against the session frame contract,
then the sender must hold the permission that the contract names for its kind (TASK-0810,
TASK-0910). The gateway start route is the only source of `session_started`, and the gateway
end route is the only source of `session_ended` (TASK-0953).
"""

from __future__ import annotations

import logging

from fastapi import WebSocket
from gateway_api.dependencies import ws_dm_manager, ws_manager
from gateway_api.session_access import has_session_permission, may_publish_frame
from gateway_api.session_frames import (
    CLIENT_FRAME_PERMISSIONS,
    InboundFrameError,
    read_session_frame,
)
from gateway_api.websocket_auth import admit_gateway_websocket
from runefoble_auth.errors import AuthzUnavailableError
from runefoble_auth.principal import VerifiedPrincipal
from runefoble_auth.websocket import action_authorizer, send_socket_error, serve_authorized_socket

logger = logging.getLogger("runefoble.gateway.session_websocket")


async def _holds_control(websocket: WebSocket, session_id: str, user_id: str) -> bool:
    """Check `session.control` once. A SpiceDB outage gives False and an error frame."""
    try:
        return await has_session_permission(session_id, user_id, "control")
    except AuthzUnavailableError:
        logger.error("SpiceDB could not check session.control for session '%s'", session_id)
        await send_socket_error(
            websocket,
            "AUTHZ_UNAVAILABLE",
            "Authorization unavailable. This socket gets no DM frames.",
            action="dm_whisper",
        )
        return False


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
        if await _holds_control(websocket, session_id, principal.user_id):
            ws_dm_manager.register(session_id, websocket)
        return True

    def close_room() -> None:
        ws_manager.disconnect(session_id, websocket)
        ws_dm_manager.disconnect(session_id, websocket)

    async def relay(principal: VerifiedPrincipal, text: str) -> None:
        try:
            kind, payload = read_session_frame(text)
        except InboundFrameError as exc:
            await send_socket_error(websocket, exc.code, exc.message)
            return
        permission = CLIENT_FRAME_PERMISSIONS[kind]
        if not await may_publish_frame(websocket, session_id, principal.user_id, kind, permission):
            return
        await ws_manager.broadcast(session_id, payload)

    await serve_authorized_socket(
        websocket,
        admit=lambda ws: admit_gateway_websocket(
            ws, action_authorizer("session.observe", session_id)
        ),
        on_open=open_room,
        on_frame=relay,
        on_close=close_room,
        receive=WebSocket.receive_text,
    )


__all__ = ["session_websocket_endpoint"]
