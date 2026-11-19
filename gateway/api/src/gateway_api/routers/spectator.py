"""Spectator stream proxy router. The state comes from the owning services.

The GET needs a verified bearer token and `session.observe`. The owners check the same token and
the same permission again. The GET has no side effect. The spectator connection event is published
when the WebSocket is admitted (see `routers/overlay.py`).
"""

from fastapi import APIRouter, Depends, Request, WebSocket
from gateway_api.auth import require_zanzibar_permission
from gateway_api.dependencies import get_upstreams
from gateway_api.spectator import (
    SpectatorStateResponse,
    SpectatorViewerInfo,
    compose_spectator_state,
)
from gateway_api.spectator_source import read_audience_views

router = APIRouter(tags=["Spectator"])


_OBSERVE = Depends(require_zanzibar_permission("observe", "session", "session_id"))


@router.get(
    "/api/v1/spectate/{session_id}",
    response_model=SpectatorStateResponse,
    dependencies=[_OBSERVE],
)
async def get_spectator_state(request: Request, session_id: str) -> SpectatorStateResponse:
    """Retrieve the audience view of the session, board, and chronicle from the owners.

    The caller needs a verified bearer token and `session.observe`. The owners verify the same
    token again. Hidden tokens, monsters, and private DM notes are not in the response.
    """
    principal = request.state.principal
    session, board = await read_audience_views(
        get_upstreams(request), session_id, request.headers.get("authorization")
    )
    viewer = SpectatorViewerInfo(viewer_id=principal.user_id, viewer_name=principal.username)
    return compose_spectator_state(session, board, viewer)


@router.websocket("/ws/spectator/{session_id}")
async def spectator_websocket_endpoint(websocket: WebSocket, session_id: str) -> None:
    """Real-time spectator WebSocket feed. Same frames as /ws/overlay/{session_id}."""
    from gateway_api.routers.overlay import overlay_websocket_endpoint

    await overlay_websocket_endpoint(websocket, session_id)
