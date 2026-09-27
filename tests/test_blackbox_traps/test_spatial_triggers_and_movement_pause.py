"""Blackbox tests for Spatial Trap Triggers and Movement Pausing (TASK-0156).

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
Verifies:
- Token movement across tactical grid checks hidden trap cells.
- Step trigger breaches immediately pause token movement at the trap coordinates.
- Proximity trigger breaches pause token movement within designated cell radius.
- Movement response flags `trap_triggered` and `movement_paused`.
- TrapSprungEvent emission and event bus publication.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from board_state.dependencies import (
    get_spicedb_client,
    set_event_bus,
    set_spicedb_client,
)
from board_state.main import app as board_app
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient
from runefoble_platform.redis_bus import MockAsyncRedis, RedisStreamsEventBus

_mock_redis: MockAsyncRedis | None = None


@pytest.fixture(autouse=True)
def setup_auth_and_bus():
    global _mock_redis
    mock_spicedb = MockSpiceDBClient()
    set_spicedb_client(mock_spicedb)
    _mock_redis = MockAsyncRedis()
    bus = RedisStreamsEventBus(client=_mock_redis)
    set_event_bus(bus)
    yield
    set_spicedb_client(SpiceDBClient())
    set_event_bus(None)


@pytest.mark.asyncio
async def test_step_trap_breach_pauses_movement():
    """Verify stepping onto a secret trap pauses token movement at the breach cell."""
    spicedb: MockSpiceDBClient = get_spicedb_client()
    client = TestClient(board_app)

    board_id = f"board-{uuid4().hex[:8]}"
    campaign_id = f"camp-{uuid4().hex[:8]}"
    dm_user = f"dm-{uuid4().hex[:6]}"

    await spicedb.write_relationship("campaign", campaign_id, "dungeon_master", "user", dm_user)
    await spicedb.write_relationship("board", board_id, "campaign", "campaign", campaign_id)

    # 1. Initialize board
    client.post("/api/v1/boards", json={"board_id": board_id, "cols": 12, "rows": 12})

    # 2. Place secret step trap at (4, 3)
    trap_res = client.post(
        f"/api/v1/boards/{board_id}/traps?campaign_id={campaign_id}",
        json={
            "name": "Secret Pressure Plate",
            "x": 4,
            "y": 3,
            "trigger_type": "step",
            "damage_dice": "1d10",
            "is_secret": True,
        },
        headers={"X-User-Id": dm_user},
    )
    assert trap_res.status_code == 201
    trap_id = trap_res.json()["trap_id"]

    # 3. Place player token Valeros at (2, 3)
    place_res = client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={"token_id": "valeros", "name": "Valeros", "x": 2, "y": 3, "is_friendly": True},
    )
    assert place_res.status_code == 200

    # 4. Player attempts to move token from (2, 3) all the way to (6, 3)
    move_res = client.post(
        f"/api/v1/boards/{board_id}/tokens/valeros/move",
        json={"to_x": 6, "to_y": 3},
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
        f"/api/v1/boards/{board_id}/traps?campaign_id={campaign_id}",
        headers={"X-User-Id": dm_user},
    )
    traps = traps_res.json()["traps"]
    sprung_trap = next(t for t in traps if t["trap_id"] == trap_id)
    assert sprung_trap["is_sprung"] is True
    assert sprung_trap["is_armed"] is False

    # 6. Verify event was published over Redis Streams
    assert _mock_redis is not None
    assert "runefoble.events.board" in _mock_redis.streams
    stream_events = _mock_redis.streams["runefoble.events.board"]
    assert any(
        e[1].get("event_type") in ("TrapSprungEvent", "runefoble.events.board.trap_sprung")
        for e in stream_events
    )


@pytest.mark.asyncio
async def test_proximity_trap_breach_pauses_movement():
    """Verify passing near a secret proximity trap pauses movement within the trigger radius."""
    spicedb: MockSpiceDBClient = get_spicedb_client()
    client = TestClient(board_app)

    board_id = f"board-{uuid4().hex[:8]}"
    campaign_id = f"camp-{uuid4().hex[:8]}"
    dm_user = f"dm-{uuid4().hex[:6]}"

    await spicedb.write_relationship("campaign", campaign_id, "dungeon_master", "user", dm_user)
    await spicedb.write_relationship("board", board_id, "campaign", "campaign", campaign_id)

    client.post("/api/v1/boards", json={"board_id": board_id, "cols": 12, "rows": 12})

    # Proximity ambush trap placed at (5, 5) with proximity_radius=1
    client.post(
        f"/api/v1/boards/{board_id}/traps?campaign_id={campaign_id}",
        json={
            "name": "Goblin Ambush Zone",
            "x": 5,
            "y": 5,
            "trigger_type": "proximity",
            "proximity_radius": 1,
            "is_secret": True,
        },
        headers={"X-User-Id": dm_user},
    )

    # Place player token Kyra at (2, 4)
    client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={"token_id": "kyra", "name": "Kyra", "x": 2, "y": 4, "is_friendly": True},
    )

    # Move along row 4 towards (8, 4)
    # The path will hit (4, 4), which is within distance 1 of (5, 5)!
    move_res = client.post(
        f"/api/v1/boards/{board_id}/tokens/kyra/move",
        json={"to_x": 8, "to_y": 4},
    )
    assert move_res.status_code == 200
    data = move_res.json()

    assert data["x"] == 4
    assert data["y"] == 4
    assert data["movement_paused"] is True
    assert data["trap_triggered"] is not None
