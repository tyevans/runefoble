"""Spectator Stream Overlay and Real-Time Broadcast Blackbox Suite (TASK-0809).

Validates, through public frontdoors and live loopback owners:
1. GET /api/v1/spectate/{id} and /api/v1/spectator/sessions/{id} need a verified bearer token
   and `session.observe`. Other viewers get 403. No token gets 401.
2. The state comes from game_session and board_state. An owner 404 passes on. No fixture data.
3. The viewer is the verified token subject. No query token or header identifies a viewer.
4. The spectator connection event is published when the WebSocket is admitted, not by the GET.
5. The live WebSocket /ws/spectator/{id} sends the owner party and camera updates.
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from gateway_api.cinematic_director import clear_cinematic_directors
from starlette.websockets import WebSocketDisconnect

from tests.helpers.ws_identity import ws_subprotocols
from tests.realtime_session import bearer, open_table

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

SPECTATOR = "spectator_sol"
STRANGER = "stranger_eve"
SPECTATE_PATHS = ("/api/v1/spectate/{sid}", "/api/v1/spectator/sessions/{sid}")
SPECTATOR_EVENT_STREAM = "runefoble.events.spectator"


@pytest.fixture(autouse=True)
def clean_directors():
    clear_cinematic_directors()
    yield
    clear_cinematic_directors()


@pytest.fixture
def table(board_table):
    """A live session with a board, a party token, a monster, and one spectator."""
    return board_table("dm_dora", {SPECTATOR: "spectator"}, start=True)


@pytest.fixture
def gateway(board_gateway: TestClient) -> TestClient:
    return board_gateway


def test_spectate_returns_owner_state_to_an_observer(gateway, table):
    _, session_id = table
    for template in SPECTATE_PATHS:
        res = gateway.get(template.format(sid=session_id), headers=bearer(SPECTATOR))
        assert res.status_code == 200, res.text
        data = res.json()

        assert data["session_id"] == session_id
        assert data["status"] == "active"
        assert data["round"] == 1
        assert (data["cols"], data["rows"]) == (8, 8)
        assert [t["name"] for t in data["tokens"]] == ["Valeros"]
        assert data["chronicle"], "the session start is in the owner chronicle"
        assert data["viewer"]["viewer_id"] == SPECTATOR


def test_spectate_omits_private_owner_fields(gateway, table):
    _, session_id = table
    data = gateway.get(SPECTATE_PATHS[0].format(sid=session_id), headers=bearer(SPECTATOR)).json()

    assert "Goblin Stalker" not in [t["name"] for t in data["tokens"]]
    for tok in data["tokens"]:
        assert set(tok) <= {"id", "name", "x", "y", "conditions", "color", "is_ai_controlled"}
    assert "dm_notes" not in data
    assert "monster_stat_blocks" not in data


def test_spectate_refuses_a_viewer_without_observe(gateway, table):
    _, session_id = table
    for template in SPECTATE_PATHS:
        res = gateway.get(template.format(sid=session_id), headers=bearer(STRANGER))
        assert res.status_code == 403


def test_spectate_needs_a_bearer_token_and_ignores_a_query_token(gateway, table):
    _, session_id = table
    for template in SPECTATE_PATHS:
        url = template.format(sid=session_id)
        assert gateway.get(url).status_code == 401
        assert gateway.get(f"{url}?token=obs_overlay").status_code == 401


def test_spectate_refuses_a_session_the_caller_cannot_observe(gateway):
    res = gateway.get(SPECTATE_PATHS[0].format(sid=uuid4()), headers=bearer("dm_dora"))
    assert res.status_code == 403


def test_spectate_passes_the_owner_404_when_the_session_has_no_board(
    gateway, game_session_upstream
):
    _, session_id = open_table(gateway, game_session_upstream, "dm_dora", {SPECTATOR: "spectator"})
    res = gateway.get(SPECTATE_PATHS[0].format(sid=session_id), headers=bearer(SPECTATOR))
    assert res.status_code == 404
    assert "Valeros" not in res.text


def test_spectate_publishes_no_event_on_get(gateway, table, mock_bus):
    _, session_id = table
    assert gateway.get(SPECTATE_PATHS[0].format(sid=session_id), headers=bearer(SPECTATOR))
    assert mock_bus.streams.get(SPECTATOR_EVENT_STREAM, []) == []


def test_spectator_connection_event_is_published_when_the_socket_is_admitted(
    gateway, table, mock_bus
):
    _, session_id = table
    with gateway.websocket_connect(
        f"/ws/spectator/{session_id}", subprotocols=ws_subprotocols(SPECTATOR)
    ) as ws:
        assert ws.receive_json()["type"] == "overlay_connected"

    events = mock_bus.streams.get(SPECTATOR_EVENT_STREAM, [])
    assert len(events) == 1
    _event_id, payload = events[0]
    assert payload["event_type"] == "runefoble.events.spectator.connected"
    assert session_id in payload["payload"]
    assert SPECTATOR in payload["payload"]


def test_spectator_websocket_sends_the_owner_party_without_monsters(gateway, table):
    _, session_id = table
    with gateway.websocket_connect(
        f"/ws/spectator/{session_id}", subprotocols=ws_subprotocols(SPECTATOR)
    ) as ws:
        msg = ws.receive_json()
        assert msg["type"] == "overlay_connected"
        assert msg["session_id"] == session_id
        assert msg["transparent"] is True

        assert [p["name"] for p in msg["party"]] == ["Valeros"]
        assert msg["party"][0]["hp"] == 45
        for member in msg["party"]:
            assert "stat_block" not in member
            assert "dm_notes" not in member
            assert "ac" not in member


def test_spectator_websocket_without_an_owner_board_closes_with_an_error(
    gateway, game_session_upstream
):
    _, session_id = open_table(gateway, game_session_upstream, "dm_dora", {SPECTATOR: "spectator"})
    with gateway.websocket_connect(
        f"/ws/spectator/{session_id}", subprotocols=ws_subprotocols(SPECTATOR)
    ) as ws:
        frame = ws.receive_json()
        assert frame["type"] == "error"
        assert frame["code"] == "UPSTREAM_UNAVAILABLE"
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_json()
    assert closed.value.code == 1011


def test_spectator_websocket_realtime_broadcast_updates(gateway, table):
    """Turn start and token move broadcast a camera target to the spectator socket."""
    _, session_id = table
    with gateway.websocket_connect(
        f"/ws/spectator/{session_id}", subprotocols=ws_subprotocols("dm_dora")
    ) as ws:
        _init = ws.receive_json()

        ws.send_json({"action": "turn_started", "character_id": "c-valeros", "token_id": "t1"})
        turn_msg = ws.receive_json()
        assert turn_msg["type"] == "camera_target_updated"
        assert turn_msg["action"] == "turn_started"
        assert turn_msg["camera"]["duration_ms"] == 300

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
