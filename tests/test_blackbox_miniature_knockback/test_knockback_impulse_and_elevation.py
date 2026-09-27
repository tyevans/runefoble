"""Blackbox tests for miniature knockback impulse and elevation physics (TASK-0171).

Governed by:
- ADR-0006: Redis Streams Distributed Domain Event Streaming
- ADR-0011: eventsource-py Core Event Sourcing
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

from board_state.dependencies import repo
from fastapi.testclient import TestClient
from runefoble_events.events import PhysicsCollisionOccurred, TokenMoved
from runefoble_platform.mock_redis import MockAsyncRedis


def _create_board(client: TestClient, cols: int = 10, rows: int = 10) -> str:
    """Helper to create a fresh tactical board via public frontdoor."""
    resp = client.post(
        "/api/v1/boards",
        json={"cols": cols, "rows": rows, "session_id": f"session-knockback-{uuid4()}"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["board_id"]


def _place_token(
    client: TestClient,
    board_id: str,
    token_id: str,
    name: str,
    x: int,
    y: int,
    token_type: str = "pc",
) -> None:
    """Helper to place a miniature token via public frontdoor."""
    resp = client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={
            "token_id": token_id,
            "name": name,
            "token_type": token_type,
            "x": x,
            "y": y,
            "is_friendly": True,
        },
    )
    assert resp.status_code == 200, resp.text


def _set_terrain_elevation(
    client: TestClient, board_id: str, x: int, y: int, elevation: int
) -> None:
    """Helper to set elevation on a board cell via public frontdoor."""
    resp = client.post(
        f"/api/v1/boards/{board_id}/terrain",
        json={
            "x": x,
            "y": y,
            "elevation": elevation,
            "terrain_type": "normal",
            "hazard": None,
        },
    )
    assert resp.status_code == 200, resp.text


def test_directional_knockback_impulse_and_mass_scaling(
    client: TestClient,
    mock_bus: MockAsyncRedis,
) -> None:
    """Verify directional knockback displaces miniatures with mass scaling and grid snapping."""
    board_id = _create_board(client, cols=10, rows=10)
    _place_token(client, board_id, "token-light", "LightToken", 2, 2)
    _place_token(client, board_id, "token-heavy", "HeavyToken", 2, 5)

    # 1. Apply 15ft knockback in +X direction to light token (mass = 1.0)
    resp_light = client.post(
        f"/api/v1/boards/{board_id}/physics/knockback",
        json={
            "token_id": "token-light",
            "direction_x": 1.0,
            "direction_y": 0.0,
            "distance_ft": 15.0,
            "mass": 1.0,
        },
    )
    assert resp_light.status_code == 200, resp_light.text
    data_light = resp_light.json()
    assert data_light["status"] == "settled"
    assert data_light["to_x"] > data_light["from_x"]
    assert data_light["to_y"] == data_light["from_y"]
    assert isinstance(data_light["to_x"], int)
    assert len(data_light["trajectory"]) > 0

    # 2. Apply same 15ft knockback to heavy token (mass = 4.0)
    resp_heavy = client.post(
        f"/api/v1/boards/{board_id}/physics/knockback",
        json={
            "token_id": "token-heavy",
            "direction_x": 1.0,
            "direction_y": 0.0,
            "distance_ft": 15.0,
            "mass": 4.0,
        },
    )
    assert resp_heavy.status_code == 200, resp_heavy.text
    data_heavy = resp_heavy.json()
    assert data_heavy["status"] == "settled"
    # Heavy mass experiences higher inertia / shorter displacement
    assert data_heavy["to_x"] >= data_heavy["from_x"]
    assert data_heavy["to_y"] == data_heavy["from_y"]
    assert data_heavy["distance_traveled_ft"] <= data_light["distance_traveled_ft"]


def test_knockback_elevation_step_fall(
    client: TestClient,
    mock_bus: MockAsyncRedis,
) -> None:
    """Verify miniature knocked over an elevation ledge falls down to ground level."""
    board_id = _create_board(client, cols=10, rows=10)

    # Cell (2, 3) is a raised plateau at elevation 2
    _set_terrain_elevation(client, board_id, 2, 3, elevation=2)
    # Target cell (4, 3) is ground level at elevation 0
    _set_terrain_elevation(client, board_id, 4, 3, elevation=0)

    _place_token(client, board_id, "fighter-cliff", "Valeros", 2, 3)

    # Shove token east (+X) by 10 feet off the elevated ledge
    resp = client.post(
        f"/api/v1/boards/{board_id}/physics/knockback",
        json={
            "token_id": "fighter-cliff",
            "direction_x": 1.0,
            "direction_y": 0.0,
            "distance_ft": 10.0,
            "mass": 1.0,
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # Verify token moved from elevation 2 to lower ground elevation 0
    assert data["from_x"] == 2
    assert data["from_y"] == 3
    assert data["to_x"] == 4
    assert data["to_y"] == 3
    assert data["elevation"] == 0.0
    assert data["status"] == "settled"

    # Verify TokenMoved event recorded in event store
    store = repo.event_store
    moved_events = [
        env.event
        for env in store._events
        if isinstance(env.event, TokenMoved)
        and getattr(env.event, "token_id", None) == "fighter-cliff"
    ]
    assert len(moved_events) >= 1
    assert moved_events[-1].to_x == 4
    assert moved_events[-1].to_y == 3


def test_knockback_obstacle_wall_collision_and_impact_energy(
    client: TestClient,
    mock_bus: MockAsyncRedis,
) -> None:
    """Verify knockback halts on high-elevation wall/cliff and records impact collision energy."""
    board_id = _create_board(client, cols=8, rows=8)
    _place_token(client, board_id, "victim-1", "Goblin", 1, 2)
    # Configure high wall at (3, 2) with elevation 3 (blocking uphill step)
    _set_terrain_elevation(client, board_id, 3, 2, elevation=3)

    # Bull rush pushing east towards the wall
    resp = client.post(
        f"/api/v1/boards/{board_id}/physics/knockback",
        json={
            "token_id": "victim-1",
            "direction_x": 1.0,
            "direction_y": 0.0,
            "distance_ft": 20.0,
            "mass": 1.5,
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["collided"] is True
    assert data["collision_type"] == "wall"
    assert data["impact_energy"] > 0
    assert data["to_x"] < 3, "Miniature must not penetrate through high wall"
    assert data["to_x"] >= 1

    # Verify PhysicsCollisionOccurred event was recorded
    store = repo.event_store
    collision_events = [
        env.event
        for env in store._events
        if isinstance(env.event, PhysicsCollisionOccurred)
        and getattr(env.event, "entity_id", None) == "victim-1"
    ]
    assert len(collision_events) >= 1
    col = collision_events[-1]
    assert col.collision_type == "wall"
    assert col.impact_energy > 0


def test_knockback_grid_boundary_snapping(
    client: TestClient,
    mock_bus: MockAsyncRedis,
) -> None:
    """Verify excessive knockback distance stops cleanly at board boundaries and snaps to discrete cells."""
    board_id = _create_board(client, cols=6, rows=6)
    _place_token(client, board_id, "edge-tok", "Rogue", 4, 3)

    # Shove token east towards edge by 30 feet (6 cells)
    resp = client.post(
        f"/api/v1/boards/{board_id}/physics/knockback",
        json={
            "token_id": "edge-tok",
            "direction_x": 1.0,
            "direction_y": 0.0,
            "distance_ft": 30.0,
            "mass": 1.0,
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["collided"] is True
    assert data["collision_type"] == "boundary"
    assert 0 <= data["to_x"] < 6
    assert 0 <= data["to_y"] < 6
    assert data["status"] == "settled"


def test_knockback_websocket_broadcast(
    client: TestClient,
    mock_bus: MockAsyncRedis,
) -> None:
    """Verify token_knockback WebSocket message broadcast on physics settlement."""
    board_id = _create_board(client)
    _place_token(client, board_id, "broadcast-tok", "Paladin", 1, 1)

    with patch(
        "board_state.routers.physics.board_ws_manager.broadcast", new_callable=AsyncMock
    ) as mock_broadcast:
        resp = client.post(
            f"/api/v1/boards/{board_id}/physics/knockback",
            json={
                "token_id": "broadcast-tok",
                "direction_x": 0.0,
                "direction_y": 1.0,
                "distance_ft": 10.0,
                "mass": 1.0,
            },
        )
        assert resp.status_code == 200, resp.text
        mock_broadcast.assert_awaited_once()
        broadcast_call = mock_broadcast.await_args
        target_board_id, payload = broadcast_call[0]
        assert target_board_id == board_id
        assert payload["type"] == "token_knockback"
        assert payload["action"] == "knockback"
        assert payload["status"] == "settled"
        assert payload["knockback"]["token_id"] == "broadcast-tok"
        assert payload["knockback"]["to_y"] == 3
