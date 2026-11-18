"""Spectator stream overlay proxy router for Runefoble Gateway API.

Both HTTP routes need a verified bearer token and `session.observe` on the session. The
state comes from the owning services. The GET has no side effect. The spectator connection
event is published when the WebSocket is admitted (see `routers/overlay.py`).
"""

from fastapi import APIRouter, Depends, Request, WebSocket
from gateway_api.auth import require_zanzibar_permission
from gateway_api.dependencies import get_upstreams
from gateway_api.spectator import (
    SpectatorStateResponse,
    SpectatorViewerInfo,
    sanitize_spectator_state,
)
from gateway_api.spectator_source import read_session_source

router = APIRouter(tags=["Spectator"])


_OBSERVE = Depends(require_zanzibar_permission("observe", "session", "session_id"))


@router.get(
    "/api/v1/spectate/{session_id}",
    response_model=SpectatorStateResponse,
    dependencies=[_OBSERVE],
)
@router.get(
    "/api/v1/spectator/sessions/{session_id}",
    response_model=SpectatorStateResponse,
    dependencies=[_OBSERVE],
)
async def get_spectator_state(request: Request, session_id: str) -> dict:
    """Retrieve audience-safe spectator view of the session, board, and chronicle.

    The caller needs a verified bearer token and `session.observe`. The owners verify the same
    token again. Hidden tokens, monsters, and private DM notes are not in the response.
    """
    principal = request.state.principal
    source = await read_session_source(
        get_upstreams(request), session_id, request.headers.get("authorization")
    )
    viewer = SpectatorViewerInfo(viewer_id=principal.user_id, viewer_name=principal.username)
    return sanitize_spectator_state(source, viewer_info=viewer)


@router.websocket("/ws/spectator/{session_id}")
async def spectator_websocket_endpoint(websocket: WebSocket, session_id: str) -> None:
    """Real-time spectator WebSocket feed delivering sanitized party and broadcast updates."""
    from gateway_api.routers.overlay import overlay_websocket_endpoint

    await overlay_websocket_endpoint(websocket, session_id)
