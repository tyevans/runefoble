"""OBS Transparent Stream Overlay and Party Vitals Router.

Exposes GET /overlay/party-vitals/{session_id} serving an alpha-transparent
party vitals HUD with sub-100ms WebSocket updates and Zanzibar sanitization.
"""

from __future__ import annotations

import contextlib
from typing import Any

from fastapi import APIRouter, Query, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from gateway_api.cinematic_director import (
    DEFAULT_DURATION_MS,
    DEFAULT_EASING,
    get_cinematic_director,
)
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
from gateway_api.spectator import get_raw_session_state

router = APIRouter(tags=["OBS Overlay"])


class OverlayConnectionManager:
    """Manages active live spectator WebSocket connections per session."""

    def __init__(self) -> None:
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
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


@router.get("/overlay/party-vitals/{session_id}", response_model=None)
async def get_party_vitals_overlay(
    request: Request,
    session_id: str,
    position: str = Query("bottom"),
    easing: str = Query(DEFAULT_EASING),
    duration: int = Query(DEFAULT_DURATION_MS),
    format: str | None = Query(None),
) -> Response:
    """Retrieve OBS-ready transparent party vitals overlay."""
    raw = get_raw_session_state(session_id)
    director = get_cinematic_director(session_id)
    vitals = sanitize_party_vitals(raw, director.current_target, position=position)

    accept = request.headers.get("accept", "") if request else ""
    if format == "json" or "application/json" in accept:
        return JSONResponse(content=vitals.model_dump())
    return HTMLResponse(
        content=render_obs_overlay_html(
            vitals, easing=easing, duration_ms=duration, position=position
        )
    )


@router.websocket("/overlay/ws/{session_id}")
@router.websocket("/ws/overlay/{session_id}")
async def overlay_websocket_endpoint(websocket: WebSocket, session_id: str) -> None:
    """Real-time spectator WebSocket feed delivering sanitized updates."""
    await ws_overlay_manager.connect(session_id, websocket)
    raw = get_raw_session_state(session_id)
    director = get_cinematic_director(session_id)
    initial = sanitize_party_vitals(raw, director.current_target)

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
            if action in ("turn_started", "TurnStarted"):
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
            elif action in ("token_moved", "move_token", "TokenMoved"):
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
            elif action in ("dice_rolled", "roll_animation", "DiceRolled"):
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
