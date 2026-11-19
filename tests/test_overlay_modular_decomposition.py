"""Frontdoor blackbox tests for the stream overlay router (TASK-0117, TASK-0809, TASK-0823).

Verifies, through public routes and live loopback owners:
1. GET /overlay/party-vitals/{session_id} returns the owner party as JSON. HTML gets 406.
2. The overlay needs a bearer token and `session.observe`. A stranger gets 403.
3. WebSocket /ws/overlay/{session_id} relays the owner camera and broadcasts rolls.
4. A malformed frame gets an INVALID_FRAME error and the socket stays open (G-12).
5. The removed duplicate paths answer 404 (G-13).
"""

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from tests.helpers.ws_identity import bearer, ws_subprotocols

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

OBSERVER = "spectator_sol"


@pytest.fixture
def table(board_table):
    """A live session with a board, a party token, a monster, and one spectator."""
    return board_table("dm_dora", {OBSERVER: "spectator"}, start=True)


@pytest.fixture
def gateway(board_gateway: TestClient) -> TestClient:
    return board_gateway


def test_frontdoor_get_party_vitals_json(gateway, table):
    _, session_id = table
    res = gateway.get(f"/overlay/party-vitals/{session_id}?format=json", headers=bearer(OBSERVER))

    assert res.status_code == 200
    data = res.json()
    assert data["session_id"] == session_id
    assert [m["name"] for m in data["party"]] == ["Valeros"]
    assert data["camera"]["reason"] == "init"
    assert data["transparent"] is True
    assert "Goblin Stalker" not in res.text


def test_frontdoor_get_party_vitals_refuses_a_stranger(gateway, table):
    _, session_id = table
    res = gateway.get(f"/overlay/party-vitals/{session_id}", headers=bearer("stranger_eve"))
    assert res.status_code == 403


def test_frontdoor_get_party_vitals_html_is_not_served(gateway, table):
    _, session_id = table
    res = gateway.get(
        f"/overlay/party-vitals/{session_id}",
        headers={**bearer(OBSERVER), "Accept": "text/html"},
    )
    assert res.status_code == 406


def test_frontdoor_websocket_overlay_ws_endpoint(gateway, table):
    """Verify WebSocket /ws/overlay/{session_id} connects and relays the owner camera."""
    _, session_id = table
    with gateway.websocket_connect(
        f"/ws/overlay/{session_id}", subprotocols=ws_subprotocols("dm_dora")
    ) as ws:
        init_msg = ws.receive_json()
        assert init_msg["type"] == "overlay_connected"
        assert init_msg["session_id"] == session_id
        assert init_msg["transparent"] is True

        ws.send_json({"action": "turn_started", "character_id": "c-hero", "token_id": "t1"})
        turn_msg = ws.receive_json()
        assert turn_msg["type"] == "camera_target_updated"
        assert turn_msg["action"] == "turn_started"
        assert turn_msg["camera"]["target_x"] == 2.0

        ws.send_json({"action": "token_moved", "token_id": "t1", "to_x": 5, "to_y": 6})
        move_msg = ws.receive_json()
        assert move_msg["type"] == "camera_target_updated"
        assert move_msg["action"] == "token_moved"
        assert move_msg["to_x"] == 5
        assert move_msg["to_y"] == 6

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


def test_frontdoor_websocket_refuses_a_malformed_frame_and_stays_open(gateway, table):
    """A roll with a non-numeric result is refused. The next valid frame still gets through."""
    _, session_id = table
    with gateway.websocket_connect(
        f"/ws/overlay/{session_id}", subprotocols=ws_subprotocols("dm_dora")
    ) as ws:
        ws.receive_json()

        ws.send_json({"action": "dice_rolled", "result": "not-a-number"})
        error = ws.receive_json()
        assert error["type"] == "error"
        assert error["code"] == "INVALID_FRAME"
        assert error["action"] == "dice_rolled"

        ws.send_json({"action": "dice_rolled", "roller_name": "Kyra", "result": "14"})
        roll_msg = ws.receive_json()
        assert roll_msg["type"] == "roll_animation"
        assert roll_msg["result"] == 14


def test_frontdoor_websocket_refuses_a_frame_that_is_not_an_object(gateway, table):
    _, session_id = table
    with gateway.websocket_connect(
        f"/ws/overlay/{session_id}", subprotocols=ws_subprotocols("dm_dora")
    ) as ws:
        ws.receive_json()
        ws.send_json([1, 2, 3])
        error = ws.receive_json()
        assert error["type"] == "error"
        assert error["code"] == "INVALID_FRAME"


def test_frontdoor_websocket_turn_started_for_an_unknown_token_is_refused(gateway, table):
    _, session_id = table
    with gateway.websocket_connect(
        f"/ws/overlay/{session_id}", subprotocols=ws_subprotocols("dm_dora")
    ) as ws:
        ws.receive_json()
        ws.send_json({"action": "turn_started", "token_id": "no-such-token"})
        error = ws.receive_json()
        assert error["type"] == "error"
        assert error["code"] == "CAMERA_REJECTED"


def test_duplicate_spectator_route_alias_is_removed(gateway, table):
    _, session_id = table
    res = gateway.get(f"/api/v1/spectator/sessions/{session_id}", headers=bearer(OBSERVER))
    assert res.status_code == 404


def test_duplicate_overlay_socket_alias_is_removed(gateway, table):
    _, session_id = table
    with (
        pytest.raises(WebSocketDisconnect),
        gateway.websocket_connect(
            f"/overlay/ws/{session_id}", subprotocols=ws_subprotocols("dm_dora")
        ) as ws,
    ):
        ws.receive_json()
