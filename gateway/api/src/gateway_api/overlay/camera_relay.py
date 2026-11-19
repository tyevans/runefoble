"""Camera relay: ask the board owner to move the camera, then tell the room.

The owner moves the camera and keeps the target. The gateway maps an owner fault to an error
frame for the sender only. The room receives a `camera_target_updated` frame only when the owner
accepts the move.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from fastapi import HTTPException, WebSocket
from gateway_api.audience_replies import CameraTarget
from gateway_api.dependencies import get_upstreams
from gateway_api.overlay.room import OverlayFeed, ws_overlay_manager
from gateway_api.overlay_frames import OverlayFrame
from gateway_api.spectator_source import focus_camera_on_move, focus_camera_on_turn
from gateway_api.upstream_errors import UpstreamRejectedError
from runefoble_auth.websocket import send_socket_error
from runefoble_platform.service_client import UpstreamError

logger = logging.getLogger("runefoble.gateway.overlay")

CAMERA_FAULTS = (UpstreamError, UpstreamRejectedError, HTTPException)


async def send_camera_error(websocket: WebSocket, exc: Exception, action: str) -> None:
    """Tell the sender that the owner did not move the camera. The room gets nothing."""
    if isinstance(exc, UpstreamRejectedError):
        logger.info("Camera focus refused by the board owner: %s", exc)
        await send_socket_error(
            websocket, "CAMERA_REJECTED", "The board owner refused the camera focus", action=action
        )
        return
    logger.warning("Camera focus unavailable: %s", exc)
    await send_socket_error(
        websocket, "CAMERA_UNAVAILABLE", "The board owner is unavailable", action=action
    )


async def _relay_camera(
    websocket: WebSocket,
    session_id: str,
    *,
    frame_action: str,
    broadcast_action: str,
    focus: Callable[[], Awaitable[CameraTarget]],
    frame_fields: dict[str, object],
) -> None:
    """Run one owner camera call. On success, broadcast the new target to the room.

    `frame_action` is the action the sender used. It names any error frame. `broadcast_action`
    is the canonical action that the room receives. `frame_fields` holds the keys that describe
    the change.
    """
    try:
        cam = await focus()
    except CAMERA_FAULTS as exc:
        await send_camera_error(websocket, exc, frame_action)
        return
    await ws_overlay_manager.broadcast(
        session_id,
        {
            "type": "camera_target_updated",
            "action": broadcast_action,
            "session_id": session_id,
            **frame_fields,
            "camera": cam.model_dump(),
        },
    )


async def relay_turn_started(
    websocket: WebSocket, session_id: str, feed: OverlayFeed, frame: OverlayFrame, action: str
) -> None:
    """Center the camera on the active token, then tell the room."""
    await _relay_camera(
        websocket,
        session_id,
        frame_action=action,
        broadcast_action="turn_started",
        focus=lambda: focus_camera_on_turn(
            get_upstreams(websocket),
            session_id,
            feed.authorization,
            {
                "token_id": frame.token_id,
                "character_id": frame.character_id,
                "duration_ms": frame.duration_ms,
                "easing": frame.easing,
            },
        ),
        frame_fields={"character_id": frame.character_id, "token_id": frame.token_id},
    )


async def relay_token_moved(
    websocket: WebSocket, session_id: str, feed: OverlayFeed, frame: OverlayFrame, action: str
) -> None:
    """Center the camera on a move destination, then tell the room."""
    token_id = frame.token_id or ""
    await _relay_camera(
        websocket,
        session_id,
        frame_action=action,
        broadcast_action="token_moved",
        focus=lambda: focus_camera_on_move(
            get_upstreams(websocket),
            session_id,
            feed.authorization,
            {
                "token_id": token_id,
                "to_x": frame.to_x,
                "to_y": frame.to_y,
                "duration_ms": frame.duration_ms,
                "easing": frame.easing,
            },
        ),
        frame_fields={"token_id": token_id, "to_x": frame.to_x, "to_y": frame.to_y},
    )
