"""Blackbox TDD tests for tabletop 3D physics engine and mesh collision integration.

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
All setup and verification are performed strictly through public HTTP API endpoints
using TestClient(app) from board_state.main and checking emitted domain events.
"""

from board_state.main import app
from fastapi.testclient import TestClient
from runefoble_events.events import DiceSettled, PhysicsCollisionOccurred
from runefoble_platform.event_sourcing import get_event_store


def test_tabletop_physics_dice_throw_and_wall_collision_knockback():
    """Verify 3D physical dice toss settling and miniature knockback collision with high walls."""
    client = TestClient(app)

    # 1. Create a tactical board via public endpoint POST /api/v1/boards
    create_resp = client.post(
        "/api/v1/boards",
        json={"cols": 12, "rows": 12, "session_id": "session-physics-e2e-1"},
    )
    assert create_resp.status_code == 200, create_resp.text
    board_data = create_resp.json()
    board_id = board_data["board_id"]
    assert board_data["cols"] == 12
    assert board_data["rows"] == 12

    # 2. Place a miniature token via POST /api/v1/boards/{id}/tokens
    tok_resp = client.post(
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
    assert tok_resp.status_code == 200, tok_resp.text

    # 3. Configure high-elevation wall cell at (4, 3) with elevation 3 (cliff/wall)
    terrain_resp = client.post(
        f"/api/v1/boards/{board_id}/terrain",
        json={
            "x": 4,
            "y": 3,
            "elevation": 3,
            "terrain_type": "normal",
            "hazard": None,
        },
    )
    assert terrain_resp.status_code == 200, terrain_resp.text

    # 4. Simulate 3D tumbling physical dice throw via POST /api/v1/boards/{id}/physics/simulate-throw
    throw_resp = client.post(
        f"/api/v1/boards/{board_id}/physics/simulate-throw",
        json={
            "dice_type": "d20",
            "origin_x": 1.0,
            "origin_y": 1.0,
            "origin_z": 2.5,
            "velocity_x": 4.0,
            "velocity_y": 4.0,
            "velocity_z": 2.0,
            "seed": 42,
        },
    )
    assert throw_resp.status_code == 200, throw_resp.text
    throw_data = throw_resp.json()

    # Verify dice toss returns final face and settled board coordinate
    assert 1 <= throw_data["face_value"] <= 20
    assert throw_data["status"] == "settled"
    assert throw_data["bounces"] >= 1
    assert len(throw_data["trajectory"]) > 0
    settled_cell = throw_data["settled_cell"]
    assert 0 <= settled_cell[0] < 12
    assert 0 <= settled_cell[1] < 12

    # Verify domain event board.dice.settled emitted into event store
    store = get_event_store()
    dice_events = [
        env.event
        for env in store._events
        if isinstance(env.event, DiceSettled)
        or getattr(env.event, "event_type", "")
        in ("runefoble.events.board.dice.settled", "board.dice.settled")
    ]
    assert len(dice_events) >= 1
    settled_event = dice_events[-1]
    assert settled_event.face_value == throw_data["face_value"]
    assert settled_event.dice_type == "d20"

    # 5. Apply knockback impulse pushing token towards the high-elevation wall at (4, 3)
    # Token at (2, 3) pushed right (+X) by 20 feet (4 cells), which would reach cell 6 without walls
    kb_resp = client.post(
        f"/api/v1/boards/{board_id}/physics/knockback",
        json={
            "token_id": "fighter-1",
            "direction_x": 1.0,
            "direction_y": 0.0,
            "distance_ft": 20.0,
            "mass": 2.0,
        },
    )
    assert kb_resp.status_code == 200, kb_resp.text
    kb_data = kb_resp.json()

    # Verify knockback halts upon colliding with high-elevation wall
    assert kb_data["collided"] is True
    assert kb_data["collision_type"] == "wall"
    assert kb_data["to_x"] < 4, (
        "Token must halt before or at the wall, not penetrate through to cell 4+"
    )
    assert kb_data["to_x"] >= 2
    assert kb_data["distance_traveled_ft"] < 20.0
    assert kb_data["impact_energy"] > 0, "Impact energy must be greater than zero upon collision"

    # 6. Verify domain event board.physics.collision emitted with impact energy
    collision_events = [
        env.event
        for env in store._events
        if (
            isinstance(env.event, PhysicsCollisionOccurred)
            or getattr(env.event, "event_type", "")
            in ("runefoble.events.board.physics.collision", "board.physics.collision")
        )
        and getattr(env.event, "entity_id", None) == "fighter-1"
    ]
    assert len(collision_events) >= 1
    col_event = collision_events[-1]
    assert col_event.collision_type == "wall"
    assert col_event.impact_energy > 0
    assert col_event.entity_id == "fighter-1"

    # 7. Verify public GET /api/v1/boards/{id} reflects updated position and collision telemetry
    get_board = client.get(f"/api/v1/boards/{board_id}")
    assert get_board.status_code == 200, get_board.text
    board_state = get_board.json()
    assert board_state["tokens"]["fighter-1"]["x"] == kb_data["to_x"]
    assert board_state["last_collision"] is not None
    assert board_state["last_collision"]["entity_id"] == "fighter-1"
    assert board_state["last_collision"]["impact_energy"] > 0
