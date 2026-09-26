"""HTML and CSS template generators for OBS stream overlays."""

from __future__ import annotations

import html
import json

from gateway_api.cinematic_director import DEFAULT_DURATION_MS, DEFAULT_EASING, CameraTarget
from gateway_api.overlay_models import PartyVitalsData


def render_overlay_html(
    session_id_or_data: str | PartyVitalsData,
    transparent: bool = True,
    theme: str = "dark",
    easing: str = DEFAULT_EASING,
    duration_ms: int = DEFAULT_DURATION_MS,
    position: str = "bottom",
) -> str:
    """Generate alpha-transparent HTML output for OBS browser sources."""
    if isinstance(session_id_or_data, str):
        from gateway_api.cinematic_director import get_cinematic_director
        from gateway_api.routers.overlay import sanitize_party_vitals
        from gateway_api.spectator import get_raw_session_state

        raw = get_raw_session_state(session_id_or_data)
        director = get_cinematic_director(session_id_or_data)
        data = sanitize_party_vitals(raw, director.current_target, position=position)
    else:
        data = session_id_or_data
        transparent = data.transparent
        if position == "bottom" and data.position != "bottom":
            position = data.position

    safe_party = json.dumps([m.model_dump() for m in data.party])
    safe_cam = json.dumps(data.camera.model_dump() if data.camera else CameraTarget().model_dump())
    safe_rolls = json.dumps([r.model_dump() for r in data.recent_rolls])

    cards_html = ""
    for member in data.party:
        pct = max(0, min(100, int((member.hp / member.max_hp) * 100))) if member.max_hp > 0 else 0
        conds = "".join(
            f'<span class="condition-badge">{html.escape(c)}</span>' for c in member.conditions
        )
        ai_badge = '<span class="ai-badge">AI STAND-IN</span>' if member.is_ai_controlled else ""
        turn = " active-turn" if member.is_active_turn else ""
        cards_html += (
            f'<div class="party-card{turn}" data-id="{html.escape(member.id)}">'
            f'<div class="card-header"><span class="member-name">{html.escape(member.name)}</span>'
            f'{ai_badge}<span class="hp-text">{member.hp}/{member.max_hp} HP</span></div>'
            f'<div class="hp-bar-track"><div class="hp-bar-fill" style="width: {pct}%;"></div></div>'
            f'<div class="conditions-row">{conds}</div></div>'
        )

    pos_style = (
        "top: 20px; left: 20px;"
        if position == "sidebar"
        else (
            "top: 20px; left: 24px; right: 24px;"
            if position == "top"
            else "bottom: 24px; left: 24px; right: 24px;"
        )
    )
    flex_dir = "column" if position == "sidebar" else "row"
    align = "flex-start" if position in ("sidebar", "top") else "flex-end"
    trans_attr = "transparent-mode" if transparent else ""

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
      flex-direction: {flex_dir};
      {pos_style}
      gap: 16px;
      align-items: {align};
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
<body data-theme="{html.escape(theme)}">
  <div id="obs-canvas" class="obs-canvas">
    <runefoble-spectator-overlay session-id="{html.escape(data.session_id)}" position="{html.escape(position)}" {trans_attr}>
      <div class="party-container">{cards_html}</div>
    </runefoble-spectator-overlay>
  </div>
  <div id="roll-banner" class="roll-banner"></div>
  <script>
    window.__RUM_DATA__ = {{
      sessionId: "{html.escape(data.session_id)}",
      party: {safe_party},
      camera: {safe_cam},
      recentRolls: {safe_rolls}
    }};
    (function initOverlayWs() {{
      const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${{proto}}//${{window.location.host}}/ws/overlay/${{window.__RUM_DATA__.sessionId}}`;
      let ws;
      function connect() {{
        try {{
          ws = new WebSocket(wsUrl);
          ws.onclose = () => setTimeout(connect, 2000);
        }} catch(e) {{
          setTimeout(connect, 2000);
        }}
      }}
      if (typeof window !== "undefined" && window.location && window.location.host) {{
        connect();
      }}
    }})();
  </script>
</body>
</html>"""


def render_obs_overlay_html(
    data: PartyVitalsData,
    easing: str = DEFAULT_EASING,
    duration_ms: int = DEFAULT_DURATION_MS,
    position: str = "bottom",
) -> str:
    """Generate alpha-transparent HTML output for OBS browser sources."""
    return render_overlay_html(
        session_id_or_data=data,
        transparent=data.transparent,
        easing=easing,
        duration_ms=duration_ms,
        position=position,
    )


__all__ = [
    "render_obs_overlay_html",
    "render_overlay_html",
]
