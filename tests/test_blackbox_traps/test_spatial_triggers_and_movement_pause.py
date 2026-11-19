"""Blackbox tests for Spatial Trap Triggers and Movement Pausing (TASK-0156).

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
Verifies:
- Token movement across tactical grid checks hidden trap cells.
- Step trigger breaches immediately pause token movement at the trap coordinates.
- Proximity trigger breaches pause token movement within designated cell radius.
- Movement response flags `trap_triggered` and `movement_paused`.
- A WebSocket `confirm_move` sends the same move fields in its `token_moved` frame.
- TrapSprungEvent emission and event bus publication.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from board_state.main import app as board_app
from fastapi.testclient import TestClient
from runefoble_auth.mock import MockSpiceDBClient

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import bearer, ws_subprotocols


@pytest.mark.asyncio
async def test_step_trap_breach_pauses_movement(
    mock_bus: MockAsyncRedis, spicedb: MockSpiceDBClient
):
    """Verify stepping onto a secret trap pauses token movement at the breach cell."""
    client = TestClient(board_app, headers=bearer("user-test"))

    board_id = f"board-{uuid4().hex[:8]}"
    campaign_id = f"camp-{uuid4().hex[:8]}"
    dm_user = f"dm-{uuid4().hex[:6]}"

    await spicedb.write_relationship("campaign", campaign_id, "dungeon_master", "user", dm_user)

    # 1. Initialize board
    client.post(
        "/api/v1/boards",
        json={"board_id": board_id, "campaign_id": campaign_id, "cols": 12, "rows": 12},
        headers=bearer(dm_user),
    )

    # 2. Place secret step trap at (4, 3)
    trap_res = client.post(
        f"/api/v1/boards/{board_id}/traps",
        json={
            "name": "Secret Pressure Plate",
            "x": 4,
            "y": 3,
            "trigger_type": "step",
            "damage_dice": "1d10",
            "is_secret": True,
        },
        headers=bearer(dm_user),
    )
    assert trap_res.status_code == 201
    trap_id = trap_res.json()["trap_id"]

    # 3. Place player token Valeros at (2, 3)
    place_res = client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={"token_id": "valeros", "name": "Valeros", "x": 2, "y": 3, "is_friendly": True},
        headers=bearer(dm_user),
    )
    assert place_res.status_code == 200

    # 4. Player attempts to move token from (2, 3) all the way to (6, 3)
    move_res = client.post(
        f"/api/v1/boards/{board_id}/tokens/valeros/move",
        json={"to_x": 6, "to_y": 3},
        headers=bearer(dm_user),
    )
    assert move_res.status_code == 200
    data = move_res.json()

    # Movement should have stopped at the trap breach cell (4, 3), NOT (6, 3)
    assert data["x"] == 4
    assert data["y"] == 3
    assert data["trap_triggered"] == trap_id
    assert data["movement_paused"] is True

    # 5. Trap should now be marked as sprung
    traps_res = client.get(
        f"/api/v1/boards/{board_id}/traps",
        headers=bearer(dm_user),
    )
    traps = traps_res.json()["traps"]
    sprung_trap = next(t for t in traps if t["trap_id"] == trap_id)
    assert sprung_trap["is_sprung"] is True
    assert sprung_trap["is_armed"] is False

    # 6. Verify event was published over Redis Streams
    assert "runefoble.events.board" in mock_bus.streams
    stream_events = mock_bus.streams["runefoble.events.board"]
    assert any(
        e[1].get("event_type") in ("TrapSprungEvent", "runefoble.events.board.trap_sprung")
        for e in stream_events
    )


@pytest.mark.asyncio
async def test_proximity_trap_breach_pauses_movement(spicedb: MockSpiceDBClient):
    """Verify passing near a secret proximity trap pauses movement within the trigger radius."""
    client = TestClient(board_app, headers=bearer("user-test"))

    board_id = f"board-{uuid4().hex[:8]}"
    campaign_id = f"camp-{uuid4().hex[:8]}"
    dm_user = f"dm-{uuid4().hex[:6]}"

    await spicedb.write_relationship("campaign", campaign_id, "dungeon_master", "user", dm_user)

    client.post(
        "/api/v1/boards",
        json={"board_id": board_id, "campaign_id": campaign_id, "cols": 12, "rows": 12},
        headers=bearer(dm_user),
    )

    # Proximity ambush trap placed at (5, 5) with proximity_radius=1
    client.post(
        f"/api/v1/boards/{board_id}/traps",
        json={
            "name": "Goblin Ambush Zone",
            "x": 5,
            "y": 5,
            "trigger_type": "proximity",
            "proximity_radius": 1,
            "is_secret": True,
        },
        headers=bearer(dm_user),
    )

    # Place player token Kyra at (2, 4)
    client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={"token_id": "kyra", "name": "Kyra", "x": 2, "y": 4, "is_friendly": True},
        headers=bearer(dm_user),
    )

    # Move along row 4 towards (8, 4)
    # The path will hit (4, 4), which is within distance 1 of (5, 5)!
    move_res = client.post(
        f"/api/v1/boards/{board_id}/tokens/kyra/move",
        json={"to_x": 8, "to_y": 4},
        headers=bearer(dm_user),
    )
    assert move_res.status_code == 200
    data = move_res.json()

    assert data["x"] == 4
    assert data["y"] == 4
    assert data["movement_paused"] is True
    assert data["trap_triggered"] is not None


@pytest.mark.asyncio
async def test_websocket_confirm_move_onto_trap_reports_pause(spicedb: MockSpiceDBClient):
    """A socket move onto a trapped path sends the same pause fields as the HTTP move."""
    client = TestClient(board_app)

    board_id = f"board-{uuid4().hex[:8]}"
    campaign_id = f"camp-{uuid4().hex[:8]}"
    dm_user = f"dm-{uuid4().hex[:6]}"

    await spicedb.write_relationship("campaign", campaign_id, "dungeon_master", "user", dm_user)

    client.post(
        "/api/v1/boards",
        json={"board_id": board_id, "campaign_id": campaign_id, "cols": 12, "rows": 12},
        headers=bearer(dm_user),
    )
    trap_res = client.post(
        f"/api/v1/boards/{board_id}/traps",
        json={"name": "Pressure Plate", "x": 4, "y": 3, "trigger_type": "step"},
        headers=bearer(dm_user),
    )
    assert trap_res.status_code == 201
    trap_id = trap_res.json()["trap_id"]
    place_res = client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={"token_id": "valeros", "name": "Valeros", "x": 2, "y": 3, "is_friendly": True},
        headers=bearer(dm_user),
    )
    assert place_res.status_code == 200

    with client.websocket_connect(
        f"/ws/boards/{board_id}", subprotocols=ws_subprotocols(dm_user)
    ) as socket:
        assert socket.receive_json()["type"] == "connected"
        socket.send_json({"action": "confirm_move", "token_id": "valeros", "to_x": 6, "to_y": 3})
        frame = socket.receive_json()

    assert frame["type"] == "token_moved"
    assert (frame["x"], frame["y"]) == (4, 3)
    assert frame["movement_paused"] is True
    assert frame["trap_triggered"] == trap_id
    assert frame["movement_cost"] == 2
    assert frame["hazard_triggered"] is None
    assert frame["damage_dice"] is None
