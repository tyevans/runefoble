"""OBS Transparent Stream Overlay and Party Vitals Router.

Exposes GET /overlay/party-vitals/{session_id} serving an alpha-transparent
party vitals HUD with sub-100ms WebSocket updates and Zanzibar sanitization.
"""

from __future__ import annotations

import contextlib
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import HTMLResponse, JSONResponse
from gateway_api.auth import require_zanzibar_permission
from gateway_api.cinematic_director import (
    DEFAULT_DURATION_MS,
    DEFAULT_EASING,
    get_cinematic_director,
)
from gateway_api.dependencies import get_event_bus, get_upstreams
from gateway_api.overlay_models import (
    PartyMemberVitals,
    PartyVitalsData,
    RollAnimationData,
    sanitize_party_vitals,
)
from gateway_api.overlay_templates import (
    render_obs_overlay_html,
    render_overlay_html,
)
from gateway_api.session_access import has_session_permission
from gateway_api.spectator_source import party_tokens, read_session_source
from gateway_api.upstream_errors import UpstreamRejectedError
from gateway_api.websocket_auth import admit_gateway_websocket
from runefoble_auth.errors import AuthzUnavailableError
from runefoble_auth.principal import VerifiedPrincipal
from runefoble_auth.websocket import (
    action_authorizer,
    bearer_token_from_subprotocols,
    send_socket_error,
)
from runefoble_events.events import SpectatorSessionConnected
from runefoble_platform.event_publish import publish_best_effort
from runefoble_platform.service_client import UpstreamError

logger = logging.getLogger("runefoble.gateway.overlay")

WS_UPSTREAM_UNAVAILABLE = 1011

router = APIRouter(tags=["OBS Overlay"])


class OverlayConnectionManager:
    """Manages active live spectator WebSocket connections per session."""

    def __init__(self) -> None:
        self.active_connections: dict[str, list[WebSocket]] = {}

    def register(self, session_id: str, websocket: WebSocket) -> None:
        """Track an admitted, accepted socket. The route accepts it first."""
        self.active_connections.setdefault(session_id, []).append(websocket)

    def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        if session_id in self.active_connections:
            conns = [ws for ws in self.active_connections[session_id] if ws != websocket]
            if conns:
                self.active_connections[session_id] = conns
            else:
                self.active_connections.pop(session_id, None)

    async def broadcast_to_session(self, session_id: str, message: dict[str, Any]) -> None:
        for ws in list(self.active_connections.get(session_id, [])):
            with contextlib.suppress(Exception):
                await ws.send_json(message)


ws_overlay_manager = OverlayConnectionManager()


@router.get(
    "/overlay/party-vitals/{session_id}",
    response_model=None,
    dependencies=[Depends(require_zanzibar_permission("observe", "session", "session_id"))],
)
async def get_party_vitals_overlay(
    request: Request,
    session_id: str,
    position: str = Query("bottom"),
    easing: str = Query(DEFAULT_EASING),
    duration: int = Query(DEFAULT_DURATION_MS),
    format: str | None = Query(None),
) -> Response:
    """Retrieve OBS-ready transparent party vitals overlay. The caller needs `session.observe`."""
    source = await read_session_source(
        get_upstreams(request), session_id, request.headers.get("authorization")
    )
    director = get_cinematic_director(session_id)
    vitals = sanitize_party_vitals(
        {**source, "tokens": party_tokens(source)}, director.current_target, position=position
    )

    accept = request.headers.get("accept", "") if request else ""
    if format == "json" or "application/json" in accept:
        return JSONResponse(content=vitals.model_dump())
    return HTMLResponse(
        content=render_obs_overlay_html(
            vitals, easing=easing, duration_ms=duration, position=position
        )
    )


async def _may_publish(websocket: WebSocket, session_id: str, user_id: str, action: str) -> bool:
    """Inbound overlay frames change what every viewer sees. They need `session.participate`."""
    try:
        allowed = await has_session_permission(session_id, user_id, "participate")
    except AuthzUnavailableError:
        await send_socket_error(
            websocket, "AUTHZ_UNAVAILABLE", "Authorization unavailable", action=action
        )
        return False
    if not allowed:
        await send_socket_error(
            websocket,
            "PERMISSION_DENIED",
            f"Action '{action}' needs session.participate",
            action=action,
        )
    return allowed


async def _read_source_for_socket(websocket: WebSocket, session_id: str) -> dict[str, Any] | None:
    """Read the session state from the owners with the caller's bearer. None when they fail."""
    bearer = bearer_token_from_subprotocols(list(websocket.scope.get("subprotocols", [])))
    authorization = f"Bearer {bearer}" if bearer else None
    try:
        return await read_session_source(get_upstreams(websocket), session_id, authorization)
    except (UpstreamError, UpstreamRejectedError, HTTPException) as exc:
        logger.warning("Overlay state unavailable for session %s: %s", session_id, exc)
        await send_socket_error(
            websocket, "UPSTREAM_UNAVAILABLE", "Session state is unavailable", action="connect"
        )
        await websocket.close(code=WS_UPSTREAM_UNAVAILABLE)
        return None


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


@router.websocket("/overlay/ws/{session_id}")
@router.websocket("/ws/overlay/{session_id}")
async def overlay_websocket_endpoint(websocket: WebSocket, session_id: str) -> None:
    """Real-time spectator WebSocket feed delivering sanitized updates."""
    principal = await admit_gateway_websocket(
        websocket, action_authorizer("session.observe", session_id)
    )
    if principal is None:
        return
    raw = await _read_source_for_socket(websocket, session_id)
    if raw is None:
        return
    ws_overlay_manager.register(session_id, websocket)
    await _publish_spectator_connected(session_id, principal)
    director = get_cinematic_director(session_id)
    initial = sanitize_party_vitals({**raw, "tokens": party_tokens(raw)}, director.current_target)

    try:
        await websocket.send_json(
            {
                "type": "overlay_connected",
                "session_id": session_id,
                "party": [m.model_dump() for m in initial.party],
                "camera": director.current_target.model_dump(),
                "recent_rolls": [r.model_dump() for r in initial.recent_rolls],
                "round": initial.round,
                "transparent": True,
            }
        )
        while True:
            data = await websocket.receive_json()
            action = data.get("action") or data.get("type") or "unknown"
            if not await _may_publish(websocket, session_id, principal.user_id, action):
                continue
            if action in ("turn_started", "runefoble.events.session.turn_started"):
                cam = director.handle_turn_started(
                    data,
                    tokens=raw.get("tokens"),
                    duration_ms=data.get("duration_ms"),
                    easing=data.get("easing"),
                )
                msg = {
                    "type": "camera_target_updated",
                    "action": "turn_started",
                    "session_id": session_id,
                    "character_id": data.get("character_id"),
                    "token_id": data.get("token_id"),
                    "camera": cam.model_dump(),
                }
                await ws_overlay_manager.broadcast_to_session(session_id, msg)
            elif action in ("token_moved", "move_token", "runefoble.events.board.token_moved"):
                token_id = str(data.get("token_id", ""))
                tokens = raw.get("tokens", [])
                if not any(
                    str(t.get("id")) == token_id
                    and (t.get("hidden") or t.get("is_secret") or t.get("secret"))
                    for t in tokens
                ):
                    cam = director.handle_token_moved(
                        data, duration_ms=data.get("duration_ms"), easing=data.get("easing")
                    )
                    msg = {
                        "type": "camera_target_updated",
                        "action": "token_moved",
                        "session_id": session_id,
                        "token_id": token_id,
                        "to_x": data.get("to_x"),
                        "to_y": data.get("to_y"),
                        "camera": cam.model_dump(),
                    }
                    await ws_overlay_manager.broadcast_to_session(session_id, msg)
            elif action in ("dice_rolled", "roll_animation"):
                msg = {
                    "type": "roll_animation",
                    "roller_name": str(data.get("roller_name", "Adventurer")),
                    "dice_formula": str(data.get("dice_formula", "1d20")),
                    "result": int(data.get("result", 0)),
                    "is_critical": bool(data.get("is_critical", False)),
                    "is_fumble": bool(data.get("is_fumble", False)),
                }
                await ws_overlay_manager.broadcast_to_session(session_id, msg)
    except WebSocketDisconnect:
        ws_overlay_manager.disconnect(session_id, websocket)


__all__ = [
    "OverlayConnectionManager",
    "PartyMemberVitals",
    "PartyVitalsData",
    "RollAnimationData",
    "get_party_vitals_overlay",
    "overlay_websocket_endpoint",
    "render_obs_overlay_html",
    "render_overlay_html",
    "router",
    "sanitize_party_vitals",
    "ws_overlay_manager",
]
