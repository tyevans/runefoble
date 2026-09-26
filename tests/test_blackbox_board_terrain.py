"""Blackbox TDD tests for tactical board terrain elevation, difficult terrain, and hazards.

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
All setup and verification are performed strictly through public HTTP API endpoints
using TestClient(app) from board_state.main.
"""

from board_state.main import app
from fastapi.testclient import TestClient
from runefoble_events.events import TokenHazardTriggered
from runefoble_platform.event_sourcing import get_event_store


def test_board_terrain_elevation_difficult_movement_and_hazard_flow():
    """Verify end-to-end tactical board terrain, elevation, difficult terrain movement, and hazards."""
    client = TestClient(app)

    # a) Create a tactical board via POST /api/v1/boards (specifying grid dimensions 10x10)
    create_resp = client.post(
        "/api/v1/boards",
        json={"cols": 10, "rows": 10, "session_id": "session-terrain-bb-1"},
    )
    assert create_resp.status_code == 200, create_resp.text
    board_data = create_resp.json()
    board_id = board_data["board_id"]
    assert board_data["cols"] == 10
    assert board_data["rows"] == 10
    assert len(board_data["tokens"]) == 0

    # b) Place a token via POST /api/v1/boards/{id}/tokens
    token_resp = client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={
            "token_id": "fighter-1",
            "name": "Valeros",
            "token_type": "pc",
            "x": 2,
            "y": 3,
            "is_friendly": True,
        },
    )
    assert token_resp.status_code == 200, token_resp.text
    token_data = token_resp.json()
    assert token_data["token_id"] == "fighter-1"
    assert token_data["x"] == 2
    assert token_data["y"] == 3

    # c) Configure terrain cell via POST /api/v1/boards/{id}/terrain:
    #    - Cell (3, 3) elevation: 2, terrain_type: 'difficult', hazard: None
    cfg_33 = client.post(
        f"/api/v1/boards/{board_id}/terrain",
        json={
            "x": 3,
            "y": 3,
            "elevation": 2,
            "terrain_type": "difficult",
            "hazard": None,
        },
    )
    assert cfg_33.status_code == 200, cfg_33.text
    cell_33_data = cfg_33.json()
    assert cell_33_data["x"] == 3
    assert cell_33_data["y"] == 3
    assert cell_33_data["elevation"] == 2
    assert cell_33_data["terrain_type"] == "difficult"
    assert cell_33_data["hazard"] is None

    #    - Cell (4, 4) elevation: 0, terrain_type: 'normal', hazard: 'lava'
    cfg_44 = client.post(
        f"/api/v1/boards/{board_id}/terrain",
        json={
            "x": 4,
            "y": 4,
            "elevation": 0,
            "terrain_type": "normal",
            "hazard": "lava",
        },
    )
    assert cfg_44.status_code == 200, cfg_44.text
    cell_44_data = cfg_44.json()
    assert cell_44_data["x"] == 4
    assert cell_44_data["y"] == 4
    assert cell_44_data["elevation"] == 0
    assert cell_44_data["terrain_type"] == "normal"
    assert cell_44_data["hazard"] == "lava"

    # d) Move token through difficult terrain via POST /api/v1/boards/{id}/tokens/{token_id}/move:
    #    - Movement calculation: moving into difficult terrain costs 2x movement budget per cell.
    # Moving from (2, 3) to (3, 3) is 1 cell of difficult terrain => cost = 2.
    # If movement budget is 1, move should be rejected.
    insufficient_move = client.post(
        f"/api/v1/boards/{board_id}/tokens/fighter-1/move",
        json={"to_x": 3, "to_y": 3, "movement_budget": 1},
    )
    assert insufficient_move.status_code == 400, "Should reject move when budget is less than cost"

    # Move with sufficient movement budget (budget=2, cost=2)
    move_diff = client.post(
        f"/api/v1/boards/{board_id}/tokens/fighter-1/move",
        json={"to_x": 3, "to_y": 3, "movement_budget": 2},
    )
    assert move_diff.status_code == 200, move_diff.text
    move_diff_data = move_diff.json()
    assert move_diff_data["x"] == 3
    assert move_diff_data["y"] == 3
    assert move_diff_data["movement_cost"] == 2

    # e) Move token onto hazard cell (4, 4):
    #    - Dispatches TokenHazardTriggered event with hazard_type='lava' and damage_dice='2d10'.
    # Moving from (3, 3) to (4, 4) into normal terrain costs 1 and triggers lava hazard.
    move_hazard = client.post(
        f"/api/v1/boards/{board_id}/tokens/fighter-1/move",
        json={"to_x": 4, "to_y": 4, "movement_budget": 5},
    )
    assert move_hazard.status_code == 200, move_hazard.text
    move_hazard_data = move_hazard.json()
    assert move_hazard_data["x"] == 4
    assert move_hazard_data["y"] == 4
    assert move_hazard_data["movement_cost"] == 1
    assert move_hazard_data["hazard_triggered"] == "lava"
    assert move_hazard_data["damage_dice"] == "2d10"

    # Verify TokenHazardTriggered event in event store stream
    store = get_event_store()
    stream_events = [
        env.event for env in store._events
        if isinstance(env.event, TokenHazardTriggered)
        and getattr(env.event, "token_id", None) == "fighter-1"
    ]
    assert len(stream_events) >= 1
    hazard_event = stream_events[-1]
    assert hazard_event.hazard_type == "lava"
    assert hazard_event.damage_dice == "2d10"
    assert hazard_event.board_id == str(board_id)

    # f) Verify GET /api/v1/boards/{id} reflects updated terrain grid, token coordinates, and active hazard status.
    get_board = client.get(f"/api/v1/boards/{board_id}")
    assert get_board.status_code == 200, get_board.text
    board_state = get_board.json()

    # Check terrain cells
    terrain_cells = board_state["terrain_cells"]
    assert "3,3" in terrain_cells or "(3, 3)" in terrain_cells
    key_33 = "3,3" if "3,3" in terrain_cells else "(3, 3)"
    assert terrain_cells[key_33]["elevation"] == 2
    assert terrain_cells[key_33]["terrain_type"] == "difficult"

    key_44 = "4,4" if "4,4" in terrain_cells else "(4, 4)"
    assert terrain_cells[key_44]["elevation"] == 0
    assert terrain_cells[key_44]["terrain_type"] == "normal"
    assert terrain_cells[key_44]["hazard"] == "lava"
    assert terrain_cells[key_44]["hazard_status"] == "active"

    # Check token coordinates and hazard status
    tokens = board_state["tokens"]
    assert "fighter-1" in tokens
    fighter = tokens["fighter-1"]
    assert fighter["x"] == 4
    assert fighter["y"] == 4
    assert fighter["active_hazard"] == "lava"
    assert fighter["hazard_status"] == "active"

    # Check active hazard status on board
    assert "lava" in board_state["active_hazards"]


def test_board_terrain_multi_cell_path_cost():
    """Verify multi-cell movement traversing normal and difficult terrain calculates correct cost."""
    client = TestClient(app)

    # Create board
    res = client.post("/api/v1/boards", json={"cols": 10, "rows": 10})
    board_id = res.json()["board_id"]

    # Place token at (1, 1)
    client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={"token_id": "scout-1", "name": "Scout", "x": 1, "y": 1},
    )

    # Set (2, 2) as difficult terrain
    client.post(
        f"/api/v1/boards/{board_id}/terrain",
        json={"x": 2, "y": 2, "elevation": 1, "terrain_type": "difficult"},
    )
    # Set (3, 3) as difficult terrain
    client.post(
        f"/api/v1/boards/{board_id}/terrain",
        json={"x": 3, "y": 3, "elevation": 1, "terrain_type": "difficult"},
    )

    # Path from (1, 1) to (3, 3): enters (2, 2) [cost 2] + (3, 3) [cost 2] = total cost 4.
    # If budget is 3, should fail
    fail_res = client.post(
        f"/api/v1/boards/{board_id}/tokens/scout-1/move",
        json={"to_x": 3, "to_y": 3, "movement_budget": 3},
    )
    assert fail_res.status_code == 400

    # If budget is 4, should succeed
    succ_res = client.post(
        f"/api/v1/boards/{board_id}/tokens/scout-1/move",
        json={"to_x": 3, "to_y": 3, "movement_budget": 4},
    )
    assert succ_res.status_code == 200
    assert succ_res.json()["movement_cost"] == 4
    assert succ_res.json()["x"] == 3
    assert succ_res.json()["y"] == 3


def test_board_token_leaves_hazard_clears_hazard_status():
    """Verify token moving off hazard cell clears active hazard status."""
    client = TestClient(app)

    res = client.post("/api/v1/boards", json={"cols": 10, "rows": 10})
    board_id = res.json()["board_id"]

    # Place token at (4, 4) with lava hazard
    client.post(
        f"/api/v1/boards/{board_id}/terrain",
        json={"x": 4, "y": 4, "elevation": 0, "hazard": "lava"},
    )
    client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={"token_id": "monk-1", "name": "Monk", "x": 4, "y": 4},
    )

    # Move to safe cell (5, 5)
    move_res = client.post(
        f"/api/v1/boards/{board_id}/tokens/monk-1/move",
        json={"to_x": 5, "to_y": 5},
    )
    assert move_res.status_code == 200
    data = move_res.json()
    assert data["x"] == 5
    assert data["y"] == 5
    assert data["active_hazard"] is None
    assert data["hazard_status"] is None

    # Check board state
    board_res = client.get(f"/api/v1/boards/{board_id}")
    monk = board_res.json()["tokens"]["monk-1"]
    assert monk["active_hazard"] is None
    assert monk["hazard_status"] is None
