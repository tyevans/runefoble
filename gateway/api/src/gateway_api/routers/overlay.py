"""OBS party vitals and live camera relay for the gateway.

The gateway relays. `board_state` owns the camera target and the party. `game_session` owns the
round. An inbound frame is validated by `OverlayFrame` before any owner call. An owner fault
returns an error frame to the sender and leaves the room unchanged.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket
from fastapi.responses import JSONResponse
from gateway_api.auth import require_zanzibar_permission
from gateway_api.dependencies import get_event_bus, get_upstreams
from gateway_api.overlay_frames import (
    ROLL_ACTIONS,
    TOKEN_MOVED_ACTIONS,
    TURN_STARTED_ACTIONS,
    OverlayFrame,
    frame_kind,
)
from gateway_api.overlay_models import (
    RollAnimationMessage,
    compose_party_vitals,
)
from gateway_api.session_access import may_publish_frame
from gateway_api.spectator_source import (
    focus_camera_on_move,
    focus_camera_on_turn,
    read_audience_views,
)
from gateway_api.upstream_errors import UpstreamRejectedError
from gateway_api.websocket_auth import admit_gateway_websocket
from pydantic import ValidationError
from runefoble_auth.principal import VerifiedPrincipal
from runefoble_auth.websocket import (
    action_authorizer,
    bearer_token_from_subprotocols,
    send_socket_error,
    serve_authorized_socket,
)
from runefoble_events.events import SpectatorSessionConnected
from runefoble_platform.event_publish import publish_best_effort
from runefoble_platform.service_client import UpstreamError
from runefoble_platform.ws_groups import WebSocketGroups

logger = logging.getLogger("runefoble.gateway.overlay")

WS_UPSTREAM_UNAVAILABLE = 1011

router = APIRouter(tags=["OBS Overlay"])


# Live spectator sockets, one WebSocket group per session. Holds no domain state.
ws_overlay_manager = WebSocketGroups[str]()


def _wants_html(request: Request, format: str | None) -> bool:
    if format == "html":
        return True
    if format == "json":
        return False
    accept = request.headers.get("accept", "")
    return "text/html" in accept and "application/json" not in accept


@router.get(
    "/overlay/party-vitals/{session_id}",
    response_model=None,
    dependencies=[Depends(require_zanzibar_permission("observe", "session", "session_id"))],
)
async def get_party_vitals_overlay(
    request: Request,
    session_id: str,
    position: str = Query("bottom"),
    format: str | None = Query(None),
) -> JSONResponse:
    """Return the party vitals and the camera target as JSON. The caller needs `session.observe`.

    The gateway serves no HTML page for this route. A request that asks for HTML gets 406.
    """
    if _wants_html(request, format):
        raise HTTPException(
            status_code=406,
            detail={
                "error": "html_not_served",
                "message": "The gateway serves JSON for the party vitals. Request format=json.",
            },
        )
    session, board = await read_audience_views(
        get_upstreams(request), session_id, request.headers.get("authorization")
    )
    return JSONResponse(content=compose_party_vitals(session, board, position).model_dump())


def _bearer_header(websocket: WebSocket) -> str | None:
    bearer = bearer_token_from_subprotocols(list(websocket.scope.get("subprotocols", [])))
    return f"Bearer {bearer}" if bearer else None


async def _publish_spectator_connected(session_id: str, principal: VerifiedPrincipal) -> None:
    """Publish the connection event once, when the socket is admitted. No GET publishes it."""
    event = SpectatorSessionConnected(
        session_id=session_id,
        viewer_id=principal.user_id,
        viewer_name=principal.username,
        connected_at=datetime.now(UTC).isoformat(),
    )
    bus = get_event_bus()
    if bus is not None:
        await publish_best_effort(bus, "runefoble.events.spectator", event)


@dataclass
class _OverlayFeed:
    """Per-socket state: the caller's bearer, forwarded to the owners on each relay."""

    authorization: str | None = None


async def _open_overlay(
    websocket: WebSocket, session_id: str, principal: VerifiedPrincipal, feed: _OverlayFeed
) -> bool:
    """Read the owner views, join the group, and send the initial state. False when an owner fails."""
    feed.authorization = _bearer_header(websocket)
    try:
        session, board = await read_audience_views(
            get_upstreams(websocket), session_id, feed.authorization
        )
    except (UpstreamError, UpstreamRejectedError, HTTPException) as exc:
        logger.warning("Overlay state unavailable for session %s: %s", session_id, exc)
        await send_socket_error(
            websocket, "UPSTREAM_UNAVAILABLE", "Session state is unavailable", action="connect"
        )
        await websocket.close(code=WS_UPSTREAM_UNAVAILABLE)
        return False
    ws_overlay_manager.register(session_id, websocket)
    await _publish_spectator_connected(session_id, principal)
    vitals = compose_party_vitals(session, board)
    await websocket.send_json(
        {
            "type": "overlay_connected",
            "session_id": session_id,
            "party": [m.model_dump() for m in vitals.party],
            "camera": vitals.camera.model_dump(),
            "round": vitals.round,
            "transparent": True,
        }
    )
    return True


async def _send_camera_error(websocket: WebSocket, exc: Exception, action: str) -> None:
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


async def _relay_turn_started(
    websocket: WebSocket,
    session_id: str,
    feed: _OverlayFeed,
    frame: OverlayFrame,
    action: str,
) -> None:
    try:
        cam = await focus_camera_on_turn(
            get_upstreams(websocket),
            session_id,
            feed.authorization,
            {
                "token_id": frame.token_id,
                "character_id": frame.character_id,
                "duration_ms": frame.duration_ms,
                "easing": frame.easing,
            },
        )
    except (UpstreamError, UpstreamRejectedError, HTTPException) as exc:
        await _send_camera_error(websocket, exc, action)
        return
    await ws_overlay_manager.broadcast(
        session_id,
        {
            "type": "camera_target_updated",
            "action": "turn_started",
            "session_id": session_id,
            "character_id": frame.character_id,
            "token_id": frame.token_id,
            "camera": cam.model_dump(),
        },
    )


async def _relay_token_moved(
    websocket: WebSocket,
    session_id: str,
    feed: _OverlayFeed,
    frame: OverlayFrame,
    action: str,
) -> None:
    token_id = frame.token_id or ""
    try:
        cam = await focus_camera_on_move(
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
        )
    except (UpstreamError, UpstreamRejectedError, HTTPException) as exc:
        await _send_camera_error(websocket, exc, action)
        return
    await ws_overlay_manager.broadcast(
        session_id,
        {
            "type": "camera_target_updated",
            "action": "token_moved",
            "session_id": session_id,
            "token_id": token_id,
            "to_x": frame.to_x,
            "to_y": frame.to_y,
            "camera": cam.model_dump(),
        },
    )


async def _handle_overlay_frame(
    websocket: WebSocket,
    session_id: str,
    principal: VerifiedPrincipal,
    feed: _OverlayFeed,
    data: Any,
) -> None:
    """Validate one inbound frame, relay its camera change or roll, and broadcast the result."""
    action = frame_kind(data)
    if not await may_publish_frame(websocket, session_id, principal.user_id, action):
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
    if action in TURN_STARTED_ACTIONS:
        await _relay_turn_started(websocket, session_id, feed, frame, action)
    elif action in TOKEN_MOVED_ACTIONS:
        await _relay_token_moved(websocket, session_id, feed, frame, action)
    elif action in ROLL_ACTIONS:
        roll = RollAnimationMessage(
            roller_name=frame.roller_name,
            dice_formula=frame.dice_formula,
            result=frame.result,
            is_critical=frame.is_critical,
            is_fumble=frame.is_fumble,
        )
        await ws_overlay_manager.broadcast(session_id, roll.model_dump())


@router.websocket("/ws/overlay/{session_id}")
async def overlay_websocket_endpoint(websocket: WebSocket, session_id: str) -> None:
    """Real-time spectator WebSocket feed. Also served at /ws/spectator/{session_id}."""
    feed = _OverlayFeed()

    async def open_feed(principal: VerifiedPrincipal) -> bool:
        return await _open_overlay(websocket, session_id, principal, feed)

    async def handle_frame(principal: VerifiedPrincipal, data: Any) -> None:
        await _handle_overlay_frame(websocket, session_id, principal, feed, data)

    await serve_authorized_socket(
        websocket,
        admit=lambda ws: admit_gateway_websocket(
            ws, action_authorizer("session.observe", session_id)
        ),
        on_open=open_feed,
        on_frame=handle_frame,
        on_close=lambda: ws_overlay_manager.disconnect(session_id, websocket),
    )


__all__ = [
    "get_party_vitals_overlay",
    "overlay_websocket_endpoint",
    "router",
    "ws_overlay_manager",
]
