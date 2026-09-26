"""Spectator stream overlay proxy router for Runefoble Gateway API."""

import contextlib
from datetime import UTC, datetime

from fastapi import APIRouter, Header, Query, WebSocket
from gateway_api.dependencies import get_event_bus
from gateway_api.spectator import (
    SpectatorStateResponse,
    SpectatorViewerInfo,
    get_raw_session_state,
    sanitize_spectator_state,
)
from runefoble_events import SpectatorSessionConnected

router = APIRouter(tags=["Spectator"])


@router.get("/api/v1/spectate/{session_id}", response_model=SpectatorStateResponse)
@router.get(
    "/api/v1/spectator/sessions/{session_id}",
    response_model=SpectatorStateResponse,
)
async def get_spectator_state(
    session_id: str,
    token: str | None = Query(None, description="Optional spectator access token"),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    authorization: str | None = Header(None, alias="Authorization"),
) -> dict:
    """Retrieve audience-safe spectator view of the session, board, and chronicle.

    Redacts hidden tokens, monster stat blocks, and private DM notes.
    Dispatches SpectatorSessionConnected event to the Redis event bus.
    """
    if token:
        viewer_id = f"spectator_{token}"
        viewer_name = f"Spectator ({token})"
    elif x_user_id:
        viewer_id = x_user_id
        viewer_name = f"Viewer {x_user_id}"
    elif authorization and authorization.startswith("Bearer "):
        bearer = authorization[7:].strip()
        viewer_id = f"viewer_{bearer}"
        viewer_name = f"Spectator ({bearer})"
    else:
        viewer_id = "spectator_guest"
        viewer_name = "Guest Spectator"

    viewer_info = SpectatorViewerInfo(viewer_id=viewer_id, viewer_name=viewer_name)

    # Dispatch SpectatorSessionConnected event to Redis bus
    event = SpectatorSessionConnected(
        session_id=session_id,
        viewer_id=viewer_id,
        viewer_name=viewer_name,
        connected_at=datetime.now(UTC).isoformat(),
    )
    bus = get_event_bus()
    if bus is not None:
        with contextlib.suppress(Exception):
            await bus.publish_event("runefoble.events.spectator", event)

    raw_state = get_raw_session_state(session_id)
    return sanitize_spectator_state(raw_state, viewer_info=viewer_info)


@router.websocket("/ws/spectator/{session_id}")
async def spectator_websocket_endpoint(websocket: WebSocket, session_id: str) -> None:
    """Real-time spectator WebSocket feed delivering sanitized party and broadcast updates."""
    from gateway_api.routers.overlay import overlay_websocket_endpoint

    await overlay_websocket_endpoint(websocket, session_id)
