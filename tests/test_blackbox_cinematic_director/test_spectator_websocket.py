"""Spectator WebSocket and microfrontend manifest blackbox tests (TASK-0190)."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_overlay_websocket_connection_and_initial_sanitized_state(client: TestClient) -> None:
    """Verify connecting to /ws/overlay/{session_id} delivers initial sanitized party state."""
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


def test_overlay_websocket_turn_started_and_token_moved_camera_updates(client: TestClient) -> None:
    """Verify WebSocket updates camera target smoothly when turn starts or token moves."""
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


def test_game_session_ui_manifest_advertises_spectator_overlay(
    session_client: TestClient,
) -> None:
    """Verify GET /ui/manifest advertises <runefoble-spectator-overlay>."""
    res = session_client.get("/ui/manifest")
    assert res.status_code == 200
    manifest = res.json()
    assert manifest["service"] == "game_session"
    assert manifest["package"] == "@runefoble/game-session-ui"
    assert "runefoble-spectator-overlay" in manifest["components"]


def test_spectator_overlay_manifest_file_and_element_export() -> None:
    """Verify services/game_session/ui/manifest.json and TypeScript element source."""
    manifest_file = REPO_ROOT / "services/game_session/ui/manifest.json"
    assert manifest_file.is_file(), "services/game_session/ui/manifest.json must exist"

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
