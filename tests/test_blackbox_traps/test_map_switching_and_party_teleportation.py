"""Blackbox tests for Battlemap Switching and Party Teleportation (TASK-0156).

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup) and Hard Invariant 1 (SpiceDB Zanzibar).
Verifies:
- Seamless multi-map switching mid-session.
- Atomic teleportation of party tokens to new spawn coordinates in a single transaction.
- Non-DM authorization rejection on map switch endpoints.
- Board dimension and background image updates.
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


@pytest.fixture(autouse=True)
def setup_auth_and_bus():
    mock_spicedb = MockSpiceDBClient()
    set_spicedb_client(mock_spicedb)
    mock_redis = MockAsyncRedis()
    bus = RedisStreamsEventBus(client=mock_redis)
    set_event_bus(bus)
    yield
    set_spicedb_client(SpiceDBClient())
    set_event_bus(None)


@pytest.mark.asyncio
async def test_battlemap_switch_and_party_teleportation():
    """Verify switching active battlemap teleports all party tokens atomically."""
    spicedb: MockSpiceDBClient = get_spicedb_client()
    client = TestClient(board_app)

    board_id = f"board-{uuid4().hex[:8]}"
    campaign_id = f"camp-{uuid4().hex[:8]}"
    dm_user = f"dm-{uuid4().hex[:6]}"
    player_user = f"player-{uuid4().hex[:6]}"

    await spicedb.write_relationship("campaign", campaign_id, "dungeon_master", "user", dm_user)
    await spicedb.write_relationship("campaign", campaign_id, "player", "user", player_user)
    await spicedb.write_relationship("board", board_id, "campaign", "campaign", campaign_id)

    # 1. Initialize board Level 1 (10x10)
    client.post("/api/v1/boards", json={"board_id": board_id, "cols": 10, "rows": 10})

    # 2. Place party tokens on Level 1
    client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={"token_id": "valeros", "name": "Valeros", "x": 1, "y": 1, "is_friendly": True},
    )
    client.post(
        f"/api/v1/boards/{board_id}/tokens",
        json={"token_id": "kyra", "name": "Kyra", "x": 1, "y": 2, "is_friendly": True},
    )

    # 3. Player attempts to switch map -> 403 Forbidden
    unauth_res = client.post(
        f"/api/v1/boards/{board_id}/switch-map?campaign_id={campaign_id}",
        json={"new_map_id": "dungeon_level_2"},
        headers={"X-User-Id": player_user},
    )
    assert unauth_res.status_code == 403

    # 4. DM switches to Level 2 (20x20) and teleports both tokens to the new dungeon entrance
    switch_res = client.post(
        f"/api/v1/boards/{board_id}/switch-map?campaign_id={campaign_id}",
        json={
            "new_map_id": "dungeon_level_2",
            "cols": 20,
            "rows": 20,
            "background_image_url": "https://assets.runefoble.com/maps/dungeon_lvl2.png",
            "token_teleports": {
                "valeros": [10, 15],
                "kyra": [10, 16],
            },
        },
        headers={"X-User-Id": dm_user},
    )
    assert switch_res.status_code == 200
    switch_data = switch_res.json()
    assert switch_data["new_map_id"] == "dungeon_level_2"
    assert switch_data["cols"] == 20
    assert switch_data["rows"] == 20
    assert switch_data["teleported_tokens"]["valeros"] == [10, 15]
    assert switch_data["teleported_tokens"]["kyra"] == [10, 16]

    # 5. Verify board state public query reflects the new map and teleported token coordinates
    board_res = client.get(f"/api/v1/boards/{board_id}")
    assert board_res.status_code == 200
    board_state = board_res.json()
    assert board_state["current_map_id"] == "dungeon_level_2"
    assert board_state["cols"] == 20
    assert board_state["rows"] == 20
    assert (
        board_state["background_image_url"] == "https://assets.runefoble.com/maps/dungeon_lvl2.png"
    )
    assert board_state["tokens"]["valeros"]["x"] == 10
    assert board_state["tokens"]["valeros"]["y"] == 15
    assert board_state["tokens"]["kyra"]["x"] == 10
    assert board_state["tokens"]["kyra"]["y"] == 16
