"""Blackbox TDD tests for tactile board kinematics and spoken ghost previews.

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
Interacts strictly through public HTTP routes and WebSockets.
"""

import time
from uuid import uuid4

import pytest
from board_state.main import app as board_app
from fastapi.testclient import TestClient
from gateway_api.auth import get_spicedb_client, set_spicedb_client
from gateway_api.main import app as gateway_app
from gateway_api.main import set_event_bus
from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient


@pytest.fixture(autouse=True)
def reset_spicedb_state():
    client = MockSpiceDBClient()
    set_spicedb_client(client)
    set_event_bus(None)
    yield
    set_spicedb_client(SpiceDBClient())
    set_event_bus(None)


def test_http_preview_endpoint_waypoint_measuring_and_terrain_hazards():
    """Verify HTTP preview endpoint calculates 5-ft increments, terrain penalties, and hazard warnings."""
    client = TestClient(board_app)
    board_id = f"board-{uuid4().hex[:8]}"

    # 1. Create 10x10 tactical board
    res = client.post("/api/v1/boards", json={"board_id": board_id, "cols": 10, "rows": 10})
    assert res.status_code == 200, res.text

    # 2. Place token 'valeros' at (1, 1)
    res = client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={"token_id": "valeros", "name": "Valeros", "x": 1, "y": 1, "is_friendly": True},
    )
    assert res.status_code == 200

    # 3. Configure terrain:
    # Cell (2, 2) is difficult terrain (+5ft penalty / cost 2)
    client.post(
        f"/api/v1/boards/{board_id}/terrain",
        json={"x": 2, "y": 2, "terrain_type": "difficult"},
    )
    # Cell (3, 3) is a lava hazard
    client.post(
        f"/api/v1/boards/{board_id}/terrain",
        json={"x": 3, "y": 3, "terrain_type": "normal", "hazard": "lava"},
    )

    # 4. Preview movement from (1, 1) to (3, 3)
    # Step 1: (2, 2) difficult => 10 ft, cost 2
    # Step 2: (3, 3) normal lava => 5 ft, cost 1 (total 15 ft, cost 3)
    preview_res = client.post(
        f"/api/v1/boards/{board_id}/tokens/valeros/preview",
        json={"to_x": 3, "to_y": 3, "movement_budget": 5},
    )
    assert preview_res.status_code == 200, preview_res.text
    data = preview_res.json()

    assert data["token_id"] == "valeros"
    assert data["token_name"] == "Valeros"
    assert data["from_x"] == 1
    assert data["from_y"] == 1
    assert data["to_x"] == 3
    assert data["to_y"] == 3
    assert data["total_distance_ft"] == 15
    assert data["base_distance_ft"] == 10
    assert data["terrain_penalty_ft"] == 5
    assert data["movement_cost"] == 3
    assert data["budget_exceeded"] is False
    assert [2, 2] in data["difficult_cells"]
    assert [3, 3] in data["hazard_cells"]
    assert data["hazard_triggered"] == "lava"
    assert data["damage_dice"] == "2d10"
    assert len(data["waypoints"]) == 2

    # 5. Verify budget exceeded flag if budget is less than required movement cost
    budget_preview = client.post(
        f"/api/v1/boards/{board_id}/tokens/valeros/preview",
        json={"to_x": 3, "to_y": 3, "movement_budget": 2},
    )
    assert budget_preview.status_code == 200
    assert budget_preview.json()["budget_exceeded"] is True

    # 6. Verify original token position remains untouched after preview
    get_board = client.get(f"/api/v1/boards/{board_id}")
    assert get_board.status_code == 200
    tok = get_board.json()["tokens"]["valeros"]
    assert tok["x"] == 1
    assert tok["y"] == 1


def test_websocket_spoken_ghost_preview_and_instant_confirmation():
    """Verify spoken ghost preview stages over WebSocket (<200ms) and commits upon confirmation."""
    client = TestClient(board_app)
    board_id = f"board-{uuid4().hex[:8]}"

    client.post("/api/v1/boards", json={"board_id": board_id, "cols": 10, "rows": 10})
    client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={"token_id": "kyra", "name": "Kyra", "x": 2, "y": 2, "is_friendly": True},
    )

    with client.websocket_connect(f"/ws/boards/{board_id}") as ws:
        connected = ws.receive_json()
        assert connected["type"] == "connected"

        # 1. Send spoken intent parsed message
        t0 = time.perf_counter()
        ws.send_json(
            {
                "type": "ghost_preview",
                "token_id": "kyra",
                "speaker_name": "Kyra",
                "raw_transcript": "Kyra advances 3 squares east",
                "to_x": 5,
                "to_y": 2,
            }
        )

        preview_msg = ws.receive_json()
        latency_ms = (time.perf_counter() - t0) * 1000
        # Sub-200ms latency check
        assert latency_ms < 200.0, f"Ghost preview took {latency_ms:.2f}ms, SLA is <200ms"

        assert preview_msg["type"] == "ghost_preview"
        assert preview_msg["status"] == "staged"
        preview_data = preview_msg["preview"]
        assert preview_data["token_id"] == "kyra"
        assert preview_data["to_x"] == 5
        assert preview_data["to_y"] == 2
        assert preview_data["total_distance_ft"] == 15
        assert len(preview_data["waypoints"]) == 3

        # Board state should not have moved yet
        board_before = client.get(f"/api/v1/boards/{board_id}").json()
        assert board_before["tokens"]["kyra"]["x"] == 2

        # 2. Confirm movement via WebSocket
        ws.send_json(
            {
                "action": "confirm_move",
                "token_id": "kyra",
                "to_x": 5,
                "to_y": 2,
            }
        )

        confirm_msg = ws.receive_json()
        assert confirm_msg["type"] == "token_moved"
        assert confirm_msg["status"] == "confirmed"
        assert confirm_msg["token_id"] == "kyra"
        assert confirm_msg["x"] == 5
        assert confirm_msg["y"] == 2

        # Verify persistent board state is updated
        board_after = client.get(f"/api/v1/boards/{board_id}").json()
        assert board_after["tokens"]["kyra"]["x"] == 5
        assert board_after["tokens"]["kyra"]["y"] == 2


def test_websocket_ghost_preview_cancellation_preserves_original_state():
    """Verify cancelling a ghost preview rolls back staging and leaves token intact."""
    client = TestClient(board_app)
    board_id = f"board-{uuid4().hex[:8]}"

    client.post("/api/v1/boards", json={"board_id": board_id, "cols": 10, "rows": 10})
    client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={"token_id": "merisiel", "name": "Merisiel", "x": 3, "y": 3, "is_friendly": True},
    )

    with client.websocket_connect(f"/ws/boards/{board_id}") as ws:
        ws.receive_json()  # Handshake

        # Stage preview
        ws.send_json(
            {
                "type": "ghost_preview",
                "token_id": "merisiel",
                "to_x": 7,
                "to_y": 3,
            }
        )
        preview_msg = ws.receive_json()
        assert preview_msg["status"] == "staged"

        # Cancel preview
        ws.send_json(
            {
                "type": "cancel_preview",
                "token_id": "merisiel",
            }
        )
        cancelled_msg = ws.receive_json()
        assert cancelled_msg["type"] == "preview_cancelled"
        assert cancelled_msg["status"] == "cancelled"
        assert cancelled_msg["token_id"] == "merisiel"

    # Verify token never moved
    board = client.get(f"/api/v1/boards/{board_id}").json()
    assert board["tokens"]["merisiel"]["x"] == 3
    assert board["tokens"]["merisiel"]["y"] == 3


def test_gateway_campaign_websocket_ghost_preview_authorization():
    """Verify SpiceDB Zanzibar permissions govern ghost preview staging on gateway campaign websocket."""
    campaign_id = "camp-ghost-auth"
    spicedb = get_spicedb_client()

    import asyncio

    # Authorize player to view campaign and move token 't-valeros'
    asyncio.run(spicedb.write_relationship("campaign", campaign_id, "view", "user", "alice"))
    asyncio.run(spicedb.write_relationship("board_token", "t-valeros", "move", "user", "alice"))

    # Authorize bob only to view
    asyncio.run(spicedb.write_relationship("campaign", campaign_id, "view", "user", "bob"))

    client = TestClient(gateway_app)

    # 1. Alice (authorized) stages ghost preview
    with client.websocket_connect(f"/ws/campaigns/{campaign_id}?user_id=alice") as ws:
        connected = ws.receive_json()
        assert connected["type"] == "connected"

        ws.send_json(
            {
                "action": "ghost_preview",
                "token_id": "t-valeros",
                "to_x": 4,
                "to_y": 4,
            }
        )
        staged = ws.receive_json()
        assert staged["action"] == "ghost_preview"
        assert staged["status"] == "applied"
        assert staged["token_id"] == "t-valeros"

    # 2. Bob (unauthorized to move t-valeros) attempts ghost preview and is denied
    with client.websocket_connect(f"/ws/campaigns/{campaign_id}?user_id=bob") as ws:
        ws.receive_json()
        ws.send_json(
            {
                "action": "ghost_preview",
                "token_id": "t-valeros",
                "to_x": 4,
                "to_y": 4,
            }
        )
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "PERMISSION_DENIED"
        assert err["action"] == "ghost_preview"
