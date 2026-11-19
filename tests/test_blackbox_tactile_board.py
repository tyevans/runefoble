"""Blackbox TDD tests for BoardState modular aggregate handlers and tactile board frontdoors.

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
Tests token placement, movement, hazards, radial actions, fog, and VFX
through public HTTP frontdoors and event-sourced aggregate reconstitution.
"""

from uuid import uuid4

import pytest
from board_state.main import app
from fastapi.testclient import TestClient

from tests.helpers.ws_identity import bearer

pytestmark = pytest.mark.usefixtures("board_campaign")

client = TestClient(app, headers=bearer("user-test"))


def test_blackbox_tactile_board_http_frontdoor_lifecycle(board_campaign: str):
    """Verify tactile board lifecycle strictly through public REST frontdoors."""
    board_id = f"board-{uuid4().hex[:8]}"

    # Create tactical board
    res_create = client.post(
        "/api/v1/boards",
        json={"campaign_id": board_campaign, "board_id": board_id, "cols": 12, "rows": 12},
    )
    assert res_create.status_code == 200

    # Place PC token
    res_place = client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={"token_id": "kyra", "name": "Kyra", "x": 2, "y": 2, "is_friendly": True},
    )
    assert res_place.status_code == 200
    assert res_place.json()["token_id"] == "kyra"

    # Configure terrain
    res_terrain = client.post(
        f"/api/v1/boards/{board_id}/terrain",
        json={"x": 3, "y": 3, "terrain_type": "difficult", "hazard": "spikes"},
    )
    assert res_terrain.status_code == 200

    # Execute movement through public route
    res_move = client.post(
        f"/api/v1/boards/{board_id}/tokens/kyra/move",
        json={"to_x": 4, "to_y": 4},
    )
    assert res_move.status_code == 200
    data_move = res_move.json()
    assert data_move["x"] == 4
    assert data_move["y"] == 4

    # Read the moved token back through the public token route
    res_read = client.get(f"/api/v1/boards/{board_id}/tokens/kyra")
    assert res_read.status_code == 200
    assert res_read.json()["x"] == 4
    assert res_read.json()["y"] == 4

    # Execute radial action through public route
    res_action = client.post(
        f"/api/v1/boards/{board_id}/tokens/kyra/action",
        json={"action": "dash"},
    )
    assert res_action.status_code == 200
    assert res_action.json()["action"] == "dash"

    # Remove token through public route
    res_remove = client.delete(f"/api/v1/boards/{board_id}/tokens/kyra")
    assert res_remove.status_code == 200
