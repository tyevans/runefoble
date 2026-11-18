"""Spectator WebSocket and microfrontend manifest blackbox tests (TASK-0190, TASK-0809)."""

import pytest
from fastapi.testclient import TestClient

from tests.helpers.ws_identity import ws_subprotocols

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.fixture
def gateway(board_gateway: TestClient) -> TestClient:
    return board_gateway


def test_overlay_websocket_connection_and_initial_sanitized_state(gateway, board_table) -> None:
    """Verify connecting to /ws/overlay/{session_id} delivers the owner party without monsters."""
    _, session_id = board_table("dm_dora", {"overlay-tester": "spectator"})
    with gateway.websocket_connect(
        f"/ws/overlay/{session_id}", subprotocols=ws_subprotocols("overlay-tester")
    ) as ws:
        msg = ws.receive_json()
        assert msg["type"] == "overlay_connected"
        assert msg["session_id"] == session_id
        assert msg["transparent"] is True

        assert [p["name"] for p in msg["party"]] == ["Valeros"]
        assert "Goblin Stalker" not in [p["name"] for p in msg["party"]]

        for member in msg["party"]:
            assert "stat_block" not in member
            assert "dm_notes" not in member
            assert "ac" not in member


def test_overlay_websocket_turn_started_and_token_moved_camera_updates(
    gateway, board_table
) -> None:
    """Verify WebSocket updates camera target smoothly when turn starts or token moves."""
    _, session_id = board_table("dm_dora")
    with gateway.websocket_connect(
        f"/ws/overlay/{session_id}", subprotocols=ws_subprotocols("dm_dora")
    ) as ws:
        _init = ws.receive_json()

        # 1. Turn Started -> broadcast camera centering
        ws.send_json({"action": "turn_started", "character_id": "c-valeros", "token_id": "t1"})
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
