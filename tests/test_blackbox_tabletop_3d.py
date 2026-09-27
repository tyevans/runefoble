"""Blackbox TDD tests for 3D miniature tokens and WebGL tabletop physics.

Governed by:
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0012: Theming System and Accessibility Contrast Invariants
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from board_state.dependencies import repo
from board_state.main import app
from fastapi.testclient import TestClient
from runefoble_events.events import DiceSettled, PhysicsCollisionOccurred


def test_board_state_microfrontend_manifest_3d_components():
    """Verify board_state microfrontend manifest advertises 3D tabletop capabilities."""
    client = TestClient(app)
    response = client.get("/ui/manifest")
    assert response.status_code == 200, response.text
    manifest = response.json()

    assert manifest["service"] == "board_state"
    assert manifest["package"] == "@runefoble/board-state-ui"
    assert "runefoble-board" in manifest["components"]
    assert "runefoble-tabletop-3d" in manifest["components"]


def test_3d_tabletop_physical_dice_simulation_and_settlement():
    """Verify 3D polyhedral dice toss resolves with physical bounces and settles reliably."""
    client = TestClient(app)

    # 1. Create a board via public HTTP frontdoor
    create_resp = client.post(
        "/api/v1/boards",
        json={"cols": 10, "rows": 10, "session_id": "session-3d-physics-dice"},
    )
    assert create_resp.status_code == 200, create_resp.text
    board_id = create_resp.json()["board_id"]

    # 2. Add an elevation cliff / wall at (5, 5)
    cliff_resp = client.post(
        f"/api/v1/boards/{board_id}/terrain",
        json={"x": 5, "y": 5, "elevation": 3, "terrain_type": "normal"},
    )
    assert cliff_resp.status_code == 200, cliff_resp.text

    # 3. Simulate a 3D physical throw directed toward the cliff
    throw_resp = client.post(
        f"/api/v1/boards/{board_id}/physics/simulate-throw",
        json={
            "dice_type": "d20",
            "origin_x": 1.0,
            "origin_y": 1.0,
            "origin_z": 3.0,
            "velocity_x": 4.5,
            "velocity_y": 4.5,
            "velocity_z": 2.5,
            "seed": 101,
        },
    )
    assert throw_resp.status_code == 200, throw_resp.text
    throw_data = throw_resp.json()

    # Verify settle parameters
    assert throw_data["status"] == "settled"
    assert 1 <= throw_data["face_value"] <= 20
    assert throw_data["bounces"] >= 1
    assert len(throw_data["trajectory"]) > 0

    # Verify emitted CloudEvent DiceSettled
    store = repo.event_store
    dice_events = [
        env.event
        for env in store._events
        if isinstance(env.event, DiceSettled)
        or getattr(env.event, "event_type", "")
        in ("runefoble.events.board.dice.settled", "board.dice.settled")
    ]
    assert len(dice_events) >= 1
    assert dice_events[-1].face_value == throw_data["face_value"]


def test_3d_miniature_knockback_impulse_and_wall_collision():
    """Verify miniature knockback momentum halts before high-elevation cliff walls."""
    client = TestClient(app)

    # 1. Create tactical board
    board_resp = client.post(
        "/api/v1/boards",
        json={"cols": 12, "rows": 12, "session_id": "session-3d-mini-knockback"},
    )
    assert board_resp.status_code == 200, board_resp.text
    board_id = board_resp.json()["board_id"]

    # 2. Place miniature token at (2, 4)
    tok_resp = client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={
            "token_id": "mini-valeros",
            "name": "Valeros",
            "token_type": "pc",
            "x": 2,
            "y": 4,
            "is_friendly": True,
        },
    )
    assert tok_resp.status_code == 200, tok_resp.text

    # 3. Create high cliff wall at (5, 4)
    terrain_resp = client.post(
        f"/api/v1/boards/{board_id}/terrain",
        json={"x": 5, "y": 4, "elevation": 4, "terrain_type": "normal"},
    )
    assert terrain_resp.status_code == 200, terrain_resp.text

    # 4. Apply 30ft knockback impulse eastward (towards cell 5)
    kb_resp = client.post(
        f"/api/v1/boards/{board_id}/physics/knockback",
        json={
            "token_id": "mini-valeros",
            "direction_x": 1.0,
            "direction_y": 0.0,
            "distance_ft": 30.0,
            "mass": 1.5,
        },
    )
    assert kb_resp.status_code == 200, kb_resp.text
    kb_data = kb_resp.json()

    # Must collide with cliff wall and stop before cell 5
    assert kb_data["collided"] is True
    assert kb_data["collision_type"] == "wall"
    assert kb_data["to_x"] < 5
    assert kb_data["to_x"] >= 2
    assert kb_data["impact_energy"] > 0

    # Verify domain event PhysicsCollisionOccurred
    store = repo.event_store
    col_events = [
        env.event
        for env in store._events
        if (
            isinstance(env.event, PhysicsCollisionOccurred)
            or getattr(env.event, "event_type", "")
            in ("runefoble.events.board.physics.collision", "board.physics.collision")
        )
        and getattr(env.event, "entity_id", None) == "mini-valeros"
    ]
    assert len(col_events) >= 1
    assert col_events[-1].collision_type == "wall"

    # 5. Verify board projection endpoint reflects updated token position and collision telemetry
    get_resp = client.get(f"/api/v1/boards/{board_id}")
    assert get_resp.status_code == 200, get_resp.text
    board = get_resp.json()
    assert board["tokens"]["mini-valeros"]["x"] == kb_data["to_x"]
    assert board["last_collision"] is not None
    assert board["last_collision"]["entity_id"] == "mini-valeros"
