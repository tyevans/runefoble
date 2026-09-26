"""Blackbox TDD tests for TASK-0056: Autonomous Cinematic Director and OBS Stream Overlay.

Verifies:
1. Sanitization Invariants: 100% exclusion of hidden traps, unrevealed monster HP, and DM notes.
2. Transparent OBS Rendering: GET /overlay/party-vitals/{session_id} serves with alpha-transparent canvas (rgba(0,0,0,0)).
3. Cinematic Director: Autonomous turn and token action centering using cubic-bezier easing within 300ms.
4. Real-time Spectator WebSocket: Sanitized event broadcasting and camera target updates.
5. Microfrontend Manifest: Vendoring and advertising of <runefoble-spectator-overlay>.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from game_session.main import app as game_session_app
from gateway_api.cinematic_director import (
    CameraTarget,
    CinematicDirector,
    clear_cinematic_directors,
    evaluate_cubic_bezier,
    get_cinematic_director,
    parse_cubic_bezier,
)
from gateway_api.main import app as gateway_app
from gateway_api.spectator import clear_raw_session_state, set_raw_session_state
from runefoble_events.board import TokenMoved
from runefoble_events.session import TurnStarted

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def clean_environment():
    """Ensure clean director and session store before and after each test."""
    clear_cinematic_directors()
    clear_raw_session_state()
    yield
    clear_cinematic_directors()
    clear_raw_session_state()


# ---------------------------------------------------------------------------
# 1. OBS Transparent Overlay Route & Sanitization Invariant Tests
# ---------------------------------------------------------------------------


def test_obs_transparent_overlay_html_rendering_and_alpha_channel():
    """Verify GET /overlay/party-vitals/{session_id} serves HTML with alpha-transparent canvas."""
    client = TestClient(gateway_app)
    res = client.get("/overlay/party-vitals/sess-obs-alpha-1")

    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    body = res.text

    # 1. Transparent OBS Rendering: alpha-transparent canvas and zero background color obstruction
    assert "rgba(0, 0, 0, 0)" in body
    assert "background: transparent" in body
    assert "obs-canvas" in body

    # 2. Party vitals delivered
    assert "Valeros" in body
    assert "45/45 HP" in body
    assert "Kyra" in body
    assert "AI STAND-IN" in body

    # 3. Sanitization Invariant: 100% exclusion of hidden traps, unrevealed monster HP, DM notes
    assert "Goblin Stalker" not in body
    assert "Mimic" not in body
    assert "Secret GM encounter notes" not in body
    assert "DC 15 Dex save" not in body
    assert "Carrying secret potion" not in body
    assert "dm_notes" not in body


def test_obs_overlay_position_and_easing_customization():
    """Verify overlay layout positioning and cubic-bezier easing parameters."""
    client = TestClient(gateway_app)

    # Test sidebar layout
    res_sidebar = client.get("/overlay/party-vitals/sess-layout-1?position=sidebar")
    assert res_sidebar.status_code == 200
    assert "flex-direction: column" in res_sidebar.text

    # Test top layout
    res_top = client.get("/overlay/party-vitals/sess-layout-1?position=top")
    assert res_top.status_code == 200
    assert "align-items: flex-start" in res_top.text

    # Test custom cubic-bezier and duration
    custom_easing = "cubic-bezier(0.42, 0.0, 0.58, 1.0)"
    res_easing = client.get(
        f"/overlay/party-vitals/sess-layout-1?easing={custom_easing}&duration=400"
    )
    assert res_easing.status_code == 200
    assert "400ms" in res_easing.text
    assert custom_easing in res_easing.text


def test_obs_party_vitals_json_format_sanitization():
    """Verify format=json provides strictly sanitized party vitals and excludes monster stats."""
    custom_state = {
        "session_id": "sess-san-json",
        "round": 4,
        "tokens": [
            {
                "id": "t-paladin",
                "name": "Sir Roderick",
                "hp": 52,
                "max_hp": 60,
                "color": "#3b82f6",
                "conditions": ["shield of faith"],
                "dm_notes": "Holding cursed amulet.",
            },
            {
                "id": "t-shadow",
                "name": "Shadow Fiend",
                "hp": 85,
                "max_hp": 85,
                "stat_block": {"cr": "5", "stealth": "+9"},
                "is_enemy": True,
                "hidden": True,
            },
        ],
        "dm_notes": "Secret pit trap at (3,2)",
        "monster_stat_blocks": {"shadow_fiend": {"ac": 16, "hp": 85}},
    }
    set_raw_session_state("sess-san-json", custom_state)

    client = TestClient(gateway_app)
    res = client.get("/overlay/party-vitals/sess-san-json?format=json")
    assert res.status_code == 200
    data = res.json()

    assert data["session_id"] == "sess-san-json"
    assert data["round"] == 4
    assert len(data["party"]) == 1

    paladin = data["party"][0]
    assert paladin["name"] == "Sir Roderick"
    assert paladin["hp"] == 52
    assert paladin["max_hp"] == 60
    assert "shield of faith" in paladin["conditions"]
    assert "dm_notes" not in paladin

    # Verify 100% exclusion of unrevealed monster HP, traps, and DM notes
    assert "dm_notes" not in data
    assert "monster_stat_blocks" not in data
    for member in data["party"]:
        assert member["name"] != "Shadow Fiend"


# ---------------------------------------------------------------------------
# 2. Cinematic Director Auto-Camera Tests
# ---------------------------------------------------------------------------


def test_cinematic_director_cubic_bezier_calculation():
    """Verify cubic-bezier math evaluation and smooth progress calculation."""
    # Standard ease: (0.25, 0.1, 0.25, 1.0)
    p1x, p1y, p2x, p2y = parse_cubic_bezier("cubic-bezier(0.25, 0.1, 0.25, 1.0)")
    assert (p1x, p1y, p2x, p2y) == (0.25, 0.1, 0.25, 1.0)

    # Boundaries
    assert evaluate_cubic_bezier(p1x, p1y, p2x, p2y, 0.0) == 0.0
    assert evaluate_cubic_bezier(p1x, p1y, p2x, p2y, 1.0) == 1.0

    # Intermediate progression is smooth and strictly monotonic
    mid = evaluate_cubic_bezier(p1x, p1y, p2x, p2y, 0.5)
    assert 0.0 < mid < 1.0

    # Interpolation of camera coordinates
    director = CinematicDirector()
    start = CameraTarget(target_x=0.0, target_y=0.0, zoom=1.0)
    end = CameraTarget(target_x=10.0, target_y=20.0, zoom=2.0)
    interp_x, interp_y, interp_zoom = director.interpolate_position(start, end, 0.5)
    assert 0.0 < interp_x < 10.0
    assert 0.0 < interp_y < 20.0
    assert 1.0 < interp_zoom < 2.0


def test_cinematic_director_turn_started_and_token_moved_tracking():
    """Verify camera centers on active token on TurnStarted and destination on TokenMoved."""
    director = get_cinematic_director("sess-cam-test")
    tokens = [
        {"id": "tok-1", "name": "Valeros", "x": 3, "y": 4},
        {"id": "tok-2", "name": "Kyra", "x": 6, "y": 7},
    ]

    # 1. TurnStarted -> Centers on active token within 300ms
    turn_event = TurnStarted(
        session_id="sess-cam-test",
        turn_number=1,
        character_id="char-valeros",
        token_id="tok-1",
    )
    cam_turn = director.handle_turn_started(turn_event, tokens=tokens)
    assert cam_turn.target_x == 3.0
    assert cam_turn.target_y == 4.0
    assert cam_turn.duration_ms == 300
    assert cam_turn.reason == "turn_started"
    assert cam_turn.active_token_id == "tok-1"

    # 2. TokenMoved -> Centers on action center (to_x, to_y) within 300ms
    from uuid import uuid4

    move_event = TokenMoved(
        aggregate_id=uuid4(),
        token_id="tok-1",
        name="Valeros",
        from_x=3,
        from_y=4,
        to_x=5,
        to_y=6,
    )
    cam_move = director.handle_token_moved(move_event)
    assert cam_move.target_x == 5.0
    assert cam_move.target_y == 6.0
    assert cam_move.duration_ms == 300
    assert cam_move.reason == "token_moved"


# ---------------------------------------------------------------------------
# 3. Real-Time Spectator WebSocket Stream Tests
# ---------------------------------------------------------------------------


def test_overlay_websocket_connection_and_initial_sanitized_state():
    """Verify connecting to /ws/overlay/{session_id} delivers initial sanitized party state."""
    client = TestClient(gateway_app)
    with client.websocket_connect("/ws/overlay/sess-ws-1") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "overlay_connected"
        assert msg["session_id"] == "sess-ws-1"
        assert msg["transparent"] is True

        party_names = [p["name"] for p in msg["party"]]
        assert "Valeros" in party_names
        assert "Kyra" in party_names
        assert "Goblin Stalker" not in party_names
        assert "Mimic Chest" not in party_names

        # Zero unrevealed monster HP numbers or DM notes in initial payload
        for member in msg["party"]:
            assert "stat_block" not in member
            assert "dm_notes" not in member
            assert "ac" not in member


def test_overlay_websocket_turn_started_and_token_moved_camera_updates():
    """Verify WebSocket updates camera target smoothly when turn starts or token moves."""
    client = TestClient(gateway_app)
    with client.websocket_connect("/ws/overlay/sess-ws-events") as ws:
        _init = ws.receive_json()

        # 1. Turn Started -> broadcast camera centering
        ws.send_json(
            {
                "action": "turn_started",
                "character_id": "c-valeros",
                "token_id": "t1",
            }
        )
        turn_msg = ws.receive_json()
        assert turn_msg["type"] == "camera_target_updated"
        assert turn_msg["action"] == "turn_started"
        assert turn_msg["camera"]["duration_ms"] == 300
        assert turn_msg["camera"]["target_x"] == 2.0
        assert turn_msg["camera"]["target_y"] == 3.0

        # 2. Token Moved -> broadcast camera centering on action destination
        ws.send_json(
            {
                "action": "token_moved",
                "token_id": "t1",
                "from_x": 2,
                "from_y": 3,
                "to_x": 4,
                "to_y": 4,
            }
        )
        move_msg = ws.receive_json()
        assert move_msg["type"] == "camera_target_updated"
        assert move_msg["action"] == "token_moved"
        assert move_msg["camera"]["target_x"] == 4.0
        assert move_msg["camera"]["target_y"] == 4.0

        # 3. Dice Rolled -> deliver roll animation
        ws.send_json(
            {
                "action": "dice_rolled",
                "roller_name": "Valeros",
                "dice_formula": "1d20 + 5",
                "result": 20,
                "is_critical": True,
            }
        )
        roll_msg = ws.receive_json()
        assert roll_msg["type"] == "roll_animation"
        assert roll_msg["roller_name"] == "Valeros"
        assert roll_msg["result"] == 20
        assert roll_msg["is_critical"] is True


# ---------------------------------------------------------------------------
# 4. Microfrontend Manifest & Component Integrity Tests
# ---------------------------------------------------------------------------


def test_game_session_ui_manifest_advertises_spectator_overlay():
    """Verify GET /ui/manifest advertises <runefoble-spectator-overlay>."""
    session_client = TestClient(game_session_app)
    res = session_client.get("/ui/manifest")
    assert res.status_code == 200
    manifest = res.json()
    assert manifest["service"] == "game_session"
    assert manifest["package"] == "@runefoble/game-session-ui"
    assert "runefoble-spectator-overlay" in manifest["components"]


def test_spectator_overlay_manifest_file_and_element_export():
    """Verify services/game_session/ui/manifest.json and TypeScript element source."""
    manifest_file = REPO_ROOT / "services/game_session/ui/manifest.json"
    assert manifest_file.is_file(), "services/game_session/ui/manifest.json must exist"
    import json

    data = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert "runefoble-spectator-overlay" in data["components"]

    comp_file = REPO_ROOT / "services/game_session/ui/src/runefoble-spectator-overlay.ts"
    assert comp_file.is_file()
    comp_code = comp_file.read_text(encoding="utf-8")
    assert "@customElement('runefoble-spectator-overlay')" in comp_code
    assert "class RunefobleSpectatorOverlay" in comp_code

    stories_file = REPO_ROOT / "services/game_session/ui/src/spectator-overlay.stories.ts"
    assert stories_file.is_file()
    stories_code = stories_file.read_text(encoding="utf-8")
    assert "DefaultPartyHUD" in stories_code
    assert "ActiveTurnFocus" in stories_code
    assert "CriticalRollAnimation" in stories_code
