"""Frontdoor blackbox tests for TASK-0117: Stream Overlay Router and HUD Templates Decomposition.

Verifies:
1. Strict line length invariants (< 200 lines for overlay.py, overlay_models.py, overlay_templates.py).
2. GET /overlay/party-vitals/{session_id} frontdoor protocol returning valid HTML and CSS styles.
3. WebSocket /overlay/ws/{session_id} frontdoor protocol delivering sanitized state and broadcasts.
4. Template rendering via render_overlay_html with transparent mode and Bauhaus theme tags.
5. Pydantic models integrity and public symbol re-exports.
"""

from pathlib import Path

from fastapi.testclient import TestClient
from gateway_api.cinematic_director import clear_cinematic_directors
from gateway_api.main import app as gateway_app
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
from gateway_api.routers.overlay import (
    OverlayConnectionManager,
    overlay_websocket_endpoint,
    ws_overlay_manager,
)
from gateway_api.spectator import clear_raw_session_state, set_raw_session_state

REPO_ROOT = Path(__file__).resolve().parent.parent


def setup_function():
    """Reset spectator and director state before each test."""
    clear_raw_session_state()
    clear_cinematic_directors()


def teardown_function():
    """Reset spectator and director state after each test."""
    clear_raw_session_state()
    clear_cinematic_directors()


def test_overlay_file_length_invariants():
    """Verify all decomposed overlay files are strictly under 200 lines (Hard Invariant 6)."""
    base_dir = REPO_ROOT / "gateway/api/src/gateway_api"
    files_to_check = [
        base_dir / "overlay_models.py",
        base_dir / "overlay_templates.py",
        base_dir / "routers/overlay.py",
    ]

    for file_path in files_to_check:
        assert file_path.is_file(), f"Expected file {file_path} to exist"
        line_count = len(file_path.read_text(encoding="utf-8").splitlines())
        assert line_count < 200, (
            f"File {file_path.name} has {line_count} lines, exceeding the 200-line strict limit"
        )


def test_frontdoor_get_party_vitals_html():
    """Verify GET /overlay/party-vitals/{session_id} returns valid HTML with embedded CSS."""
    client = TestClient(gateway_app)
    res = client.get("/overlay/party-vitals/sess-decomp-1")

    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    body = res.text
    assert "<!DOCTYPE html>" in body
    assert "rgba(0, 0, 0, 0)" in body
    assert "background: transparent" in body
    assert "runefoble-spectator-overlay" in body
    assert "window.__RUM_DATA__" in body


def test_frontdoor_get_party_vitals_json():
    """Verify GET /overlay/party-vitals/{session_id}?format=json returns sanitized Pydantic model dict."""
    client = TestClient(gateway_app)
    res = client.get("/overlay/party-vitals/sess-decomp-2?format=json")

    assert res.status_code == 200
    data = res.json()
    assert data["session_id"] == "sess-decomp-2"
    assert "party" in data
    assert "camera" in data
    assert data["transparent"] is True


def test_frontdoor_websocket_overlay_ws_endpoint():
    """Verify WebSocket /overlay/ws/{session_id} connects and delivers sanitized real-time feeds."""
    client = TestClient(gateway_app)
    with client.websocket_connect("/overlay/ws/sess-decomp-ws-1") as ws:
        init_msg = ws.receive_json()
        assert init_msg["type"] == "overlay_connected"
        assert init_msg["session_id"] == "sess-decomp-ws-1"
        assert init_msg["transparent"] is True

        # Test turn_started broadcast over /overlay/ws/
        ws.send_json({"action": "turn_started", "character_id": "c-hero", "token_id": "t1"})
        turn_msg = ws.receive_json()
        assert turn_msg["type"] == "camera_target_updated"
        assert turn_msg["action"] == "turn_started"

        # Test token_moved broadcast over /overlay/ws/
        ws.send_json({"action": "token_moved", "token_id": "t1", "to_x": 5, "to_y": 6})
        move_msg = ws.receive_json()
        assert move_msg["type"] == "camera_target_updated"
        assert move_msg["action"] == "token_moved"
        assert move_msg["to_x"] == 5
        assert move_msg["to_y"] == 6

        # Test dice_rolled broadcast over /overlay/ws/
        ws.send_json(
            {
                "action": "dice_rolled",
                "roller_name": "Wizard",
                "dice_formula": "2d6 + 3",
                "result": 11,
                "is_critical": False,
            }
        )
        roll_msg = ws.receive_json()
        assert roll_msg["type"] == "roll_animation"
        assert roll_msg["roller_name"] == "Wizard"
        assert roll_msg["result"] == 11


def test_render_overlay_html_template_with_session_and_theme():
    """Verify render_overlay_html works directly with session_id string, transparency, and theme."""
    custom_state = {
        "session_id": "sess-direct-render",
        "tokens": [
            {"id": "t-fighter", "name": "Boran", "hp": 30, "max_hp": 30, "is_ai_controlled": True},
        ],
    }
    set_raw_session_state("sess-direct-render", custom_state)

    html_out = render_overlay_html("sess-direct-render", transparent=True, theme="bauhaus-dark")
    assert "sess-direct-render" in html_out
    assert 'data-theme="bauhaus-dark"' in html_out
    assert "Boran" in html_out
    assert "AI STAND-IN" in html_out
    assert "transparent-mode" in html_out


def test_exports_and_models_integrity():
    """Verify all re-exported and newly modularized symbols are importable."""
    assert PartyMemberVitals is not None
    assert PartyVitalsData is not None
    assert RollAnimationData is not None
    assert sanitize_party_vitals is not None
    assert render_obs_overlay_html is not None
    assert render_overlay_html is not None
    assert OverlayConnectionManager is not None
    assert overlay_websocket_endpoint is not None
    assert ws_overlay_manager is not None
