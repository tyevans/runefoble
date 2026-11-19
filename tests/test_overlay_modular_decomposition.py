"""Frontdoor blackbox tests for TASK-0117: Stream Overlay Router and HUD Templates (TASK-0809).

Verifies, through public routes and live loopback owners:
1. GET /overlay/party-vitals/{session_id} returns HTML with the transparent template markers.
2. The same route with `format=json` returns the sanitized projection.
3. The overlay needs a bearer token and `session.observe`. A stranger gets 403.
4. WebSocket /overlay/ws/{session_id} delivers sanitized state and broadcasts.
"""

import pytest
from fastapi.testclient import TestClient
from gateway_api.cinematic_director import clear_cinematic_directors

from tests.helpers.ws_identity import bearer, ws_subprotocols

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

OBSERVER = "spectator_sol"


@pytest.fixture(autouse=True)
def clean_directors():
    clear_cinematic_directors()
    yield
    clear_cinematic_directors()


@pytest.fixture
def table(board_table):
    """A live session with a board, a party token, a monster, and one spectator."""
    return board_table("dm_dora", {OBSERVER: "spectator"}, start=True)


@pytest.fixture
def gateway(board_gateway: TestClient) -> TestClient:
    return board_gateway


def test_frontdoor_get_party_vitals_html(gateway, table):
    _, session_id = table
    res = gateway.get(f"/overlay/party-vitals/{session_id}", headers=bearer(OBSERVER))

    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    body = res.text
    assert "<!DOCTYPE html>" in body
    assert "rgba(0, 0, 0, 0)" in body
    assert "background: transparent" in body
    assert "runefoble-spectator-overlay" in body
    assert "window.__RUM_DATA__" in body
    assert "Valeros" in body
    assert "Goblin Stalker" not in body


def test_frontdoor_get_party_vitals_json(gateway, table):
    _, session_id = table
    res = gateway.get(f"/overlay/party-vitals/{session_id}?format=json", headers=bearer(OBSERVER))

    assert res.status_code == 200
    data = res.json()
    assert data["session_id"] == session_id
    assert [m["name"] for m in data["party"]] == ["Valeros"]
    assert "camera" in data
    assert data["transparent"] is True


def test_frontdoor_get_party_vitals_refuses_a_stranger(gateway, table):
    _, session_id = table
    res = gateway.get(f"/overlay/party-vitals/{session_id}", headers=bearer("stranger_eve"))
    assert res.status_code == 403


def test_frontdoor_websocket_overlay_ws_endpoint(gateway, table):
    """Verify WebSocket /overlay/ws/{session_id} connects and delivers sanitized real-time feeds."""
    _, session_id = table
    with gateway.websocket_connect(
        f"/overlay/ws/{session_id}", subprotocols=ws_subprotocols("dm_dora")
    ) as ws:
        init_msg = ws.receive_json()
        assert init_msg["type"] == "overlay_connected"
        assert init_msg["session_id"] == session_id
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
