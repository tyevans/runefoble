"""OBS Transparent Stream Overlay and Party Vitals Router.

Exposes GET /overlay/party-vitals/{session_id} serving an alpha-transparent
party vitals HUD with sub-100ms WebSocket updates and Zanzibar sanitization.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    WebSocket,
)
from fastapi.responses import HTMLResponse, JSONResponse
from gateway_api.auth import require_zanzibar_permission
from gateway_api.cinematic_director import (
    DEFAULT_DURATION_MS,
    DEFAULT_EASING,
    get_cinematic_director,
)
from gateway_api.dependencies import get_upstreams
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
from gateway_api.session_access import may_publish_frame
from gateway_api.spectator_source import party_tokens, read_session_source
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
from runefoble_platform.ws_groups import WebSocketGroups

logger = logging.getLogger("runefoble.gateway.overlay")

WS_UPSTREAM_UNAVAILABLE = 1011

router = APIRouter(tags=["OBS Overlay"])


# Live spectator sockets, one WebSocket group per session.
ws_overlay_manager = WebSocketGroups[str]()


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


@dataclass
class _OverlayFeed:
    """The source state that one overlay socket reads when it opens."""

    raw: dict[str, Any] = field(default_factory=dict)


async def _open_overlay(
    websocket: WebSocket, session_id: str, principal: VerifiedPrincipal, feed: _OverlayFeed
) -> bool:
    """Read the source, join the group, and send the initial state. False when the owners fail."""
    raw = await _read_source_for_socket(websocket, session_id)
    if raw is None:
        return False
    feed.raw = raw
    ws_overlay_manager.register(session_id, websocket)
    director = get_cinematic_director(session_id)
    initial = sanitize_party_vitals({**raw, "tokens": party_tokens(raw)}, director.current_target)
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
    return True


async def _handle_overlay_frame(
    websocket: WebSocket,
    session_id: str,
    principal: VerifiedPrincipal,
    feed: _OverlayFeed,
    data: dict[str, Any],
) -> None:
    """Apply one inbound frame to the camera or the roll feed, then broadcast the result."""
    action = data.get("action") or data.get("type") or "unknown"
    if not await may_publish_frame(websocket, session_id, principal.user_id, action):
        return
    director = get_cinematic_director(session_id)
    if action in ("turn_started", "runefoble.events.session.turn_started"):
        cam = director.handle_turn_started(
            data,
            tokens=feed.raw.get("tokens"),
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
        await ws_overlay_manager.broadcast(session_id, msg)
    elif action in ("token_moved", "move_token", "runefoble.events.board.token_moved"):
        token_id = str(data.get("token_id", ""))
        tokens = feed.raw.get("tokens", [])
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
            await ws_overlay_manager.broadcast(session_id, msg)
    elif action in ("dice_rolled", "roll_animation"):
        msg = {
            "type": "roll_animation",
            "roller_name": str(data.get("roller_name", "Adventurer")),
            "dice_formula": str(data.get("dice_formula", "1d20")),
            "result": int(data.get("result", 0)),
            "is_critical": bool(data.get("is_critical", False)),
            "is_fumble": bool(data.get("is_fumble", False)),
        }
        await ws_overlay_manager.broadcast(session_id, msg)


@router.websocket("/overlay/ws/{session_id}")
@router.websocket("/ws/overlay/{session_id}")
async def overlay_websocket_endpoint(websocket: WebSocket, session_id: str) -> None:
    """Real-time spectator WebSocket feed delivering sanitized updates."""
    feed = _OverlayFeed()

    async def open_feed(principal: VerifiedPrincipal) -> bool:
        return await _open_overlay(websocket, session_id, principal, feed)

    async def handle_frame(principal: VerifiedPrincipal, data: dict[str, Any]) -> None:
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
