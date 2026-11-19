"""OBS party vitals and live camera relay routes for the gateway.

The gateway relays. `board_state` owns the camera target and the party. `game_session` owns the
round. This module holds the HTTP and WebSocket routes. The frame handling lives in
`gateway_api.overlay`. An owner fault returns an error frame to the sender and leaves the room
unchanged.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket
from fastapi.responses import JSONResponse
from gateway_api.auth import require_zanzibar_permission
from gateway_api.dependencies import get_upstreams
from gateway_api.overlay.frame_dispatch import handle_overlay_frame
from gateway_api.overlay.room import OverlayFeed, ws_overlay_manager
from gateway_api.overlay_models import compose_party_vitals
from gateway_api.spectator_source import read_audience_views
from gateway_api.upstream_errors import UpstreamRejectedError
from gateway_api.websocket_auth import admit_gateway_websocket
from runefoble_auth.principal import VerifiedPrincipal
from runefoble_auth.websocket import (
    action_authorizer,
    bearer_token_from_subprotocols,
    send_socket_error,
    serve_authorized_socket,
)
from runefoble_platform.service_client import UpstreamError

logger = logging.getLogger("runefoble.gateway.overlay")

WS_UPSTREAM_UNAVAILABLE = 1011

router = APIRouter(tags=["OBS Overlay"])


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
    dependencies=[Depends(require_zanzibar_permission("observe", "game_session", "session_id"))],
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


async def _open_overlay(
    websocket: WebSocket, session_id: str, principal: VerifiedPrincipal, feed: OverlayFeed
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


@router.websocket("/ws/overlay/{session_id}")
async def overlay_websocket_endpoint(websocket: WebSocket, session_id: str) -> None:
    """Real-time spectator WebSocket feed. Also served at /ws/spectator/{session_id}."""
    feed = OverlayFeed()

    async def open_feed(principal: VerifiedPrincipal) -> bool:
        return await _open_overlay(websocket, session_id, principal, feed)

    async def handle_frame(principal: VerifiedPrincipal, data: Any) -> None:
        await handle_overlay_frame(websocket, session_id, principal, feed, data)

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
]
