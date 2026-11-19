"""Inbound frame handling for the overlay and spectator sockets.

A frame that does not match `OverlayFrame` gets an `INVALID_FRAME` error and nothing is relayed.
A valid frame goes to the handler in `HANDLERS` for its action. An action with no row is ignored.
To add an action, add one row to `HANDLERS`.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import WebSocket
from gateway_api.overlay.camera_relay import relay_token_moved, relay_turn_started
from gateway_api.overlay.room import OverlayFeed, ws_overlay_manager
from gateway_api.overlay_frames import (
    ROLL_ACTIONS,
    TOKEN_MOVED_ACTIONS,
    TURN_STARTED_ACTIONS,
    OverlayFrame,
    frame_kind,
)
from gateway_api.overlay_models import RollAnimationMessage
from gateway_api.session_access import may_publish_frame
from pydantic import ValidationError
from runefoble_auth.principal import VerifiedPrincipal
from runefoble_auth.websocket import send_socket_error

# Every overlay frame changes what spectators see, so the sender must take part in the session.
OVERLAY_FRAME_PERMISSION = "participate"

FrameHandler = Callable[[WebSocket, str, OverlayFeed, OverlayFrame, str], Awaitable[None]]


async def _handle_roll(
    websocket: WebSocket, session_id: str, feed: OverlayFeed, frame: OverlayFrame, action: str
) -> None:
    roll = RollAnimationMessage(
        roller_name=frame.roller_name,
        dice_formula=frame.dice_formula,
        result=frame.result,
        is_critical=frame.is_critical,
        is_fumble=frame.is_fumble,
    )
    await ws_overlay_manager.broadcast(session_id, roll.model_dump())


# Action name to handler. Each action in one tuple shares its handler.
_ROUTES: tuple[tuple[tuple[str, ...], FrameHandler], ...] = (
    (TURN_STARTED_ACTIONS, relay_turn_started),
    (TOKEN_MOVED_ACTIONS, relay_token_moved),
    (ROLL_ACTIONS, _handle_roll),
)
HANDLERS: dict[str, FrameHandler] = {
    action: handler for actions, handler in _ROUTES for action in actions
}


async def handle_overlay_frame(
    websocket: WebSocket,
    session_id: str,
    principal: VerifiedPrincipal,
    feed: OverlayFeed,
    data: Any,
) -> None:
    """Check the publish right, validate one inbound frame, then run its handler."""
    action = frame_kind(data)
    if not await may_publish_frame(
        websocket, session_id, principal.user_id, action, OVERLAY_FRAME_PERMISSION
    ):
        return
    try:
        frame = OverlayFrame.model_validate(data)
    except ValidationError:
        await send_socket_error(
            websocket,
            "INVALID_FRAME",
            "The frame does not match the overlay schema",
            action=action,
        )
        return
    handler = HANDLERS.get(action)
    if handler is not None:
        await handler(websocket, session_id, feed, frame, action)
