"""Blackbox TDD tests for tactile board kinematics and route previews.

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
Interacts strictly through public HTTP routes and WebSockets.
"""

from uuid import uuid4

from board_state.main import app
from fastapi.testclient import TestClient


def test_tactile_kinematics_route_previews():
    """Verify route preview calculations via HTTP frontdoors."""
    client = TestClient(app)
    board_id = f"board-{uuid4().hex[:8]}"

    # Create board
    res = client.post("/api/v1/boards", json={"board_id": board_id, "cols": 10, "rows": 10})
    assert res.status_code == 200

    # Place token
    res = client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={"token_id": "valeros", "name": "Valeros", "x": 1, "y": 1, "is_friendly": True},
    )
    assert res.status_code == 200

    # Configure difficult terrain at (2, 2)
    client.post(
        f"/api/v1/boards/{board_id}/terrain",
        json={"x": 2, "y": 2, "terrain_type": "difficult"},
    )

    # Preview move via token endpoint
    res_token_preview = client.post(
        f"/api/v1/boards/{board_id}/tokens/valeros/preview",
        json={"to_x": 3, "to_y": 3, "movement_budget": 10},
    )
    assert res_token_preview.status_code == 200
    data = res_token_preview.json()
    assert data["token_id"] == "valeros"
    assert data["total_distance_ft"] == 15
    assert data["movement_cost"] == 3

    # Preview move via /preview endpoint
    res_preview = client.post(
        f"/api/v1/boards/{board_id}/preview",
        json={"token_id": "valeros", "to_x": 3, "to_y": 3, "movement_budget": 10},
    )
    assert res_preview.status_code == 200
    assert res_preview.json()["total_distance_ft"] == 15

    # Preview move via /preview-move alias
    res_preview_alias = client.post(
        f"/api/v1/boards/{board_id}/preview-move",
        json={"token_id": "valeros", "to_x": 3, "to_y": 3, "movement_budget": 10},
    )
    assert res_preview_alias.status_code == 200
    assert res_preview_alias.json()["total_distance_ft"] == 15


def test_tactile_kinematics_websocket_flow():
    """Verify WebSocket live kinematics stream and ghost preview staging."""
    client = TestClient(app)
    board_id = f"board-{uuid4().hex[:8]}"

    client.post("/api/v1/boards", json={"board_id": board_id, "cols": 10, "rows": 10})
    client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={"token_id": "merisiel", "name": "Merisiel", "x": 2, "y": 2, "is_friendly": True},
    )

    with client.websocket_connect(f"/ws/boards/{board_id}") as ws:
        handshake = ws.receive_json()
        assert handshake["type"] == "connected"

        # Stage ghost preview
        ws.send_json(
            {
                "type": "ghost_preview",
                "token_id": "merisiel",
                "to_x": 4,
                "to_y": 2,
            }
        )
        staged = ws.receive_json()
        assert staged["type"] == "ghost_preview"
        assert staged["status"] == "staged"
        assert staged["preview"]["to_x"] == 4

        # Confirm movement
        ws.send_json(
            {
                "action": "confirm_move",
                "token_id": "merisiel",
                "to_x": 4,
                "to_y": 2,
            }
        )
        confirmed = ws.receive_json()
        assert confirmed["type"] == "token_moved"
        assert confirmed["status"] == "confirmed"
        assert confirmed["x"] == 4

    # Verify board state
    board = client.get(f"/api/v1/boards/{board_id}").json()
    assert board["tokens"]["merisiel"]["x"] == 4
