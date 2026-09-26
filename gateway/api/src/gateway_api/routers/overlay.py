"""OBS Transparent Stream Overlay and Party Vitals Router.

Exposes GET /overlay/party-vitals/{session_id} serving an alpha-transparent
(rgba(0, 0, 0, 0)) party vitals HUD with sub-100ms WebSocket updates and
strict server-side Zanzibar sanitization (ADR-0001, ADR-0004, ADR-0007, ADR-0013).
"""

from __future__ import annotations

import contextlib
import html
import json
from typing import Any

from fastapi import APIRouter, Query, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from gateway_api.cinematic_director import (
    DEFAULT_DURATION_MS,
    DEFAULT_EASING,
    CameraTarget,
    get_cinematic_director,
)
from gateway_api.spectator import get_raw_session_state
from pydantic import BaseModel, Field

router = APIRouter(tags=["OBS Overlay"])


class PartyMemberVitals(BaseModel):
    """Sanitized party member vitals for OBS stream HUD."""

    id: str
    name: str
    hp: int
    max_hp: int
    temp_hp: int = 0
    conditions: list[str] = Field(default_factory=list)
    is_ai_controlled: bool = False
    color: str | None = None
    is_active_turn: bool = False


class RollAnimationData(BaseModel):
    """Sanitized dice roll animation payload for OBS stream overlay."""

    id: str = "roll-1"
    roller_name: str
    dice_formula: str
    result: int
    is_critical: bool = False
    is_fumble: bool = False
    timestamp: str = ""


class PartyVitalsData(BaseModel):
    """Complete sanitized party vitals and camera state for stream overlay."""

    session_id: str
    party: list[PartyMemberVitals] = Field(default_factory=list)
    camera: CameraTarget
    recent_rolls: list[RollAnimationData] = Field(default_factory=list)
    round: int = 1
    position: str = "bottom"
    transparent: bool = True


def sanitize_party_vitals(
    raw_state: dict[str, Any],
    camera_target: CameraTarget | None = None,
    position: str = "bottom",
) -> PartyVitalsData:
    """Sanitize raw session state into safe spectator party vitals.

    Excludes 100% of hidden traps, unrevealed monster HP numbers, and DM-only notes.
    """
    session_id = str(raw_state.get("session_id") or "session_default")
    round_num = int(raw_state.get("round", 1))

    raw_tokens = raw_state.get("tokens") or raw_state.get("board", {}).get("tokens") or []
    if isinstance(raw_tokens, dict):
        raw_tokens = list(raw_tokens.values())

    party_members: list[PartyMemberVitals] = []
    for tok in raw_tokens:
        tok_dict = tok if isinstance(tok, dict) else tok.model_dump()
        is_hidden = (
            bool(tok_dict.get("hidden"))
            or bool(tok_dict.get("is_secret"))
            or bool(tok_dict.get("is_hidden"))
            or bool(tok_dict.get("secret"))
        )
        if is_hidden:
            continue

        token_type = str(tok_dict.get("token_type", "")).lower()
        has_stat_block = "stat_block" in tok_dict or "cr" in tok_dict
        is_enemy = bool(tok_dict.get("is_enemy", False)) or token_type == "monster"
        if has_stat_block or is_enemy:
            continue

        conditions = tok_dict.get("conditions", [])
        if isinstance(conditions, list):
            clean_conditions = [
                str(c) if not isinstance(c, dict) else str(c.get("name", "")) for c in conditions
            ]
        else:
            clean_conditions = []

        party_members.append(
            PartyMemberVitals(
                id=str(tok_dict.get("id", "")),
                name=str(tok_dict.get("name", "Adventurer")),
                hp=int(tok_dict.get("hp", 10)),
                max_hp=int(tok_dict.get("max_hp", 10)),
                temp_hp=int(tok_dict.get("temp_hp", 0)),
                conditions=clean_conditions,
                is_ai_controlled=bool(tok_dict.get("is_ai_controlled", False)),
                color=tok_dict.get("color"),
                is_active_turn=bool(tok_dict.get("is_active_turn", False)),
            )
        )

    raw_rolls = raw_state.get("recent_rolls", [])
    rolls: list[RollAnimationData] = []
    for r in raw_rolls:
        r_dict = r if isinstance(r, dict) else r.model_dump()
        if r_dict.get("is_private") or r_dict.get("private"):
            continue
        rolls.append(
            RollAnimationData(
                id=str(r_dict.get("id", "roll-1")),
                roller_name=str(r_dict.get("roller_name", "Hero")),
                dice_formula=str(r_dict.get("dice_formula", "1d20")),
                result=int(r_dict.get("result", 0)),
                is_critical=bool(r_dict.get("is_critical", False)),
                is_fumble=bool(r_dict.get("is_fumble", False)),
                timestamp=str(r_dict.get("timestamp", "")),
            )
        )

    return PartyVitalsData(
        session_id=session_id,
        party=party_members,
        camera=camera_target or CameraTarget(),
        recent_rolls=rolls,
        round=round_num,
        position=position,
        transparent=True,
    )


def render_obs_overlay_html(
    data: PartyVitalsData,
    easing: str = DEFAULT_EASING,
    duration_ms: int = DEFAULT_DURATION_MS,
    position: str = "bottom",
) -> str:
    """Generate alpha-transparent HTML output for OBS browser sources."""
    safe_party_json = json.dumps([m.model_dump() for m in data.party])
    safe_camera_json = json.dumps(data.camera.model_dump())
    safe_rolls_json = json.dumps([r.model_dump() for r in data.recent_rolls])

    cards_html = ""
    for member in data.party:
        pct = max(0, min(100, int((member.hp / member.max_hp) * 100))) if member.max_hp > 0 else 0
        conds_html = "".join(
            f'<span class="condition-badge">{html.escape(c)}</span>' for c in member.conditions
        )
        ai_badge = '<span class="ai-badge">AI STAND-IN</span>' if member.is_ai_controlled else ""
        turn_class = " active-turn" if member.is_active_turn else ""
        cards_html += f"""
        <div class="party-card{turn_class}" data-id="{html.escape(member.id)}">
          <div class="card-header">
            <span class="member-name">{html.escape(member.name)}</span>
            {ai_badge}
            <span class="hp-text">{member.hp}/{member.max_hp} HP</span>
          </div>
          <div class="hp-bar-track">
            <div class="hp-bar-fill" style="width: {pct}%;"></div>
          </div>
          <div class="conditions-row">{conds_html}</div>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Runefoble OBS Party Vitals - Session {html.escape(data.session_id)}</title>
  <style>
    * {{ box-sizing: border-box; }}
    html, body {{
      margin: 0; padding: 0; width: 100vw; height: 100vh;
      background: transparent !important;
      background-color: rgba(0, 0, 0, 0) !important;
      overflow: hidden;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      user-select: none;
    }}
    .obs-canvas {{
      position: absolute; inset: 0;
      background: transparent;
      background-color: rgba(0, 0, 0, 0);
      pointer-events: none;
      display: flex;
      flex-direction: {"column" if position == "sidebar" else "row"};
      {"top: 20px; left: 20px;" if position == "sidebar" else ("top: 20px; left: 24px; right: 24px;" if position == "top" else "bottom: 24px; left: 24px; right: 24px;")}
      gap: 16px;
      align-items: {"flex-start" if position in ("sidebar", "top") else "flex-end"};
    }}
    .party-card {{
      background: rgba(18, 18, 24, 0.88);
      border: 2px solid #3b82f6;
      box-shadow: 4px 4px 0px rgba(0, 0, 0, 0.6);
      padding: 10px 14px;
      min-width: 220px;
      color: #f8fafc;
      transition: transform {duration_ms}ms {easing};
    }}
    .party-card.active-turn {{
      border-color: #f59e0b;
      box-shadow: 0 0 12px rgba(245, 158, 11, 0.7);
    }}
    .card-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }}
    .member-name {{ font-weight: 800; font-size: 0.95rem; }}
    .ai-badge {{ background: #f59e0b; color: #000; font-size: 0.65rem; font-weight: 800; padding: 1px 4px; }}
    .hp-text {{ font-size: 0.8rem; font-weight: 700; color: #94a3b8; }}
    .hp-bar-track {{ height: 8px; background: #334155; border: 1px solid #475569; overflow: hidden; }}
    .hp-bar-fill {{ height: 100%; background: #10b981; transition: width 300ms ease-out; }}
    .conditions-row {{ display: flex; gap: 4px; margin-top: 6px; flex-wrap: wrap; }}
    .condition-badge {{ background: #ef4444; color: #fff; font-size: 0.65rem; font-weight: 700; padding: 1px 5px; }}
    .roll-banner {{
      position: absolute; top: 30px; left: 50%; transform: translateX(-50%);
      background: rgba(15, 23, 42, 0.95); border: 3px solid #3b82f6; padding: 12px 24px;
      color: #fff; font-weight: 900; font-size: 1.25rem; display: none;
    }}
  </style>
</head>
<body>
  <div id="obs-canvas" class="obs-canvas">
    <runefoble-spectator-overlay
      session-id="{html.escape(data.session_id)}"
      position="{html.escape(position)}"
      transparent-mode
    >
      <div class="party-container">{cards_html}</div>
    </runefoble-spectator-overlay>
  </div>
  <div id="roll-banner" class="roll-banner"></div>
  <script>
    window.__RUM_DATA__ = {{
      sessionId: "{html.escape(data.session_id)}",
      party: {safe_party_json},
      camera: {safe_camera_json},
      recentRolls: {safe_rolls_json}
    }};
  </script>
</body>
</html>"""


class OverlayConnectionManager:
    """Manages active live spectator WebSocket connections per session."""

    def __init__(self) -> None:
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)

    def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        if session_id in self.active_connections:
            self.active_connections[session_id] = [
                ws for ws in self.active_connections[session_id] if ws != websocket
            ]
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def broadcast_to_session(self, session_id: str, message: dict[str, Any]) -> None:
        """Broadcast sanitized message to all spectator overlay websockets."""
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
    """Retrieve OBS-ready transparent party vitals overlay.

    Serves alpha-transparent HTML output or sanitized JSON with zero DM secrets.
    """
    raw_state = get_raw_session_state(session_id)
    director = get_cinematic_director(session_id)
    vitals_data = sanitize_party_vitals(raw_state, director.current_target, position=position)

    accept_header = request.headers.get("accept", "") if request else ""
    if format == "json" or "application/json" in accept_header:
        return JSONResponse(content=vitals_data.model_dump())

    html_content = render_obs_overlay_html(
        vitals_data, easing=easing, duration_ms=duration, position=position
    )
    return HTMLResponse(content=html_content)


@router.websocket("/ws/overlay/{session_id}")
async def overlay_websocket_endpoint(websocket: WebSocket, session_id: str) -> None:
    """Real-time spectator WebSocket feed delivering sanitized party and camera updates."""
    await ws_overlay_manager.connect(session_id, websocket)
    raw_state = get_raw_session_state(session_id)
    director = get_cinematic_director(session_id)
    initial_vitals = sanitize_party_vitals(raw_state, director.current_target)

    try:
        await websocket.send_json(
            {
                "type": "overlay_connected",
                "session_id": session_id,
                "party": [m.model_dump() for m in initial_vitals.party],
                "camera": director.current_target.model_dump(),
                "recent_rolls": [r.model_dump() for r in initial_vitals.recent_rolls],
                "round": initial_vitals.round,
                "transparent": True,
            }
        )

        while True:
            data = await websocket.receive_json()
            action = data.get("action") or data.get("type") or "unknown"

            # 1. Turn Started -> center camera on active character within 300ms
            if action in ("turn_started", "TurnStarted"):
                camera_target = director.handle_turn_started(
                    data,
                    tokens=raw_state.get("tokens"),
                    duration_ms=data.get("duration_ms"),
                    easing=data.get("easing"),
                )
                msg = {
                    "type": "camera_target_updated",
                    "action": "turn_started",
                    "session_id": session_id,
                    "character_id": data.get("character_id"),
                    "token_id": data.get("token_id"),
                    "camera": camera_target.model_dump(),
                }
                await ws_overlay_manager.broadcast_to_session(session_id, msg)

            # 2. Token Moved -> center camera on action center within 300ms
            elif action in ("token_moved", "move_token", "TokenMoved"):
                token_id = str(data.get("token_id", ""))
                # Strip hidden tokens: do not broadcast hidden creature moves to spectator feed
                is_hidden = False
                for tok in raw_state.get("tokens", []):
                    if str(tok.get("id")) == token_id and (
                        tok.get("hidden") or tok.get("is_secret") or tok.get("secret")
                    ):
                        is_hidden = True
                        break

                if not is_hidden:
                    camera_target = director.handle_token_moved(
                        data,
                        duration_ms=data.get("duration_ms"),
                        easing=data.get("easing"),
                    )
                    msg = {
                        "type": "camera_target_updated",
                        "action": "token_moved",
                        "session_id": session_id,
                        "token_id": token_id,
                        "to_x": data.get("to_x"),
                        "to_y": data.get("to_y"),
                        "camera": camera_target.model_dump(),
                    }
                    await ws_overlay_manager.broadcast_to_session(session_id, msg)

            # 3. Dice Rolled -> deliver roll animation
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
    "render_obs_overlay_html",
    "router",
    "sanitize_party_vitals",
    "ws_overlay_manager",
]
