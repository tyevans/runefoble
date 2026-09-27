"""Blackbox tests for Secret DM Grid Layer and Zanzibar Authorization (TASK-0156).

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup) and Hard Invariant 1 (SpiceDB Zanzibar).
Verifies:
- DM-only secret trap creation enforced via SpiceDB Zanzibar permissions.
- Player exclusion from secret trap markers on GET /boards/{board_id}/traps.
- Authorized DM visibility of both secret and public markers.
- CloudEvents registration and specification conformance.
- Trap disarming workflow.
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
from eventsource.domain.event_registry import get_event_class_or_none
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient
from runefoble_events.board_traps import (
    BattlemapSwitchedEvent,
    TrapDisarmedEvent,
    TrapPlacedEvent,
    TrapSprungEvent,
)


@pytest.fixture(autouse=True)
def setup_auth_and_bus():
    mock_spicedb = MockSpiceDBClient()
    set_spicedb_client(mock_spicedb)
    set_event_bus(None)
    yield
    set_spicedb_client(SpiceDBClient())
    set_event_bus(None)


def test_board_traps_cloudevents_registration():
    """Verify that all domain events for traps and map switching conform to CloudEvents 1.0."""
    for event_cls, expected_type in [
        (TrapPlacedEvent, "runefoble.events.board.trap_placed"),
        (TrapSprungEvent, "runefoble.events.board.trap_sprung"),
        (TrapDisarmedEvent, "runefoble.events.board.trap_disarmed"),
        (BattlemapSwitchedEvent, "runefoble.events.board.battlemap_switched"),
    ]:
        resolved = get_event_class_or_none(expected_type)
        assert resolved == event_cls, (
            f"Event {event_cls.__name__} not registered for {expected_type}"
        )

    evt = TrapPlacedEvent(
        trap_id="trap-test-1",
        board_id="board-test-1",
        name="Pit Trap",
        x=3,
        y=4,
        trigger_type="step",
        damage_dice="2d6",
    )
    ce = evt.to_cloudevent_dict()
    assert ce["specversion"] == "1.0"
    assert ce["type"] == "runefoble.events.board.trap_placed"
    assert ce["data"]["name"] == "Pit Trap"
    assert ce["data"]["damage_dice"] == "2d6"


@pytest.mark.asyncio
async def test_zanzibar_dm_trap_creation_and_player_masking():
    """Verify non-DM players cannot place secret traps and cannot query secret markers."""
    spicedb: MockSpiceDBClient = get_spicedb_client()
    client = TestClient(board_app)

    board_id = f"board-{uuid4().hex[:8]}"
    campaign_id = f"camp-{uuid4().hex[:8]}"
    dm_user = f"dm-{uuid4().hex[:6]}"
    player_user = f"player-{uuid4().hex[:6]}"

    # Set up SpiceDB Zanzibar relationships: Evelyn is DM, Alice is Player
    await spicedb.write_relationship("campaign", campaign_id, "dungeon_master", "user", dm_user)
    await spicedb.write_relationship("campaign", campaign_id, "player", "user", player_user)
    await spicedb.write_relationship("board", board_id, "campaign", "campaign", campaign_id)

    # 1. Initialize board via public frontdoor
    init_res = client.post("/api/v1/boards", json={"board_id": board_id, "cols": 12, "rows": 12})
    assert init_res.status_code == 200

    # 2. Unauthorized player attempts to create a secret trap -> 403 Forbidden
    unauth_post = client.post(
        f"/api/v1/boards/{board_id}/traps?campaign_id={campaign_id}",
        json={"name": "Player Sneaky Trap", "x": 5, "y": 5, "is_secret": True},
        headers={"X-User-Id": player_user},
    )
    assert unauth_post.status_code == 403
    assert "Forbidden" in unauth_post.json()["detail"]

    # 3. Authorized DM creates a secret pit trap at (4, 4)
    auth_post = client.post(
        f"/api/v1/boards/{board_id}/traps?campaign_id={campaign_id}",
        json={
            "name": "Secret Spiked Pit",
            "x": 4,
            "y": 4,
            "trigger_type": "step",
            "dc_detection": 16,
            "damage_dice": "2d10",
            "is_secret": True,
        },
        headers={"X-User-Id": dm_user},
    )
    assert auth_post.status_code == 201
    trap_data = auth_post.json()
    trap_id = trap_data["trap_id"]
    assert trap_data["name"] == "Secret Spiked Pit"
    assert trap_data["is_secret"] is True

    # 4. DM also creates a visible/revealed obstacle trap at (8, 8)
    client.post(
        f"/api/v1/boards/{board_id}/traps?campaign_id={campaign_id}",
        json={"name": "Visible Barricade", "x": 8, "y": 8, "is_secret": False},
        headers={"X-User-Id": dm_user},
    )

    # 5. Player queries traps -> secret traps MUST be masked; only visible trap returned
    player_get = client.get(
        f"/api/v1/boards/{board_id}/traps?campaign_id={campaign_id}",
        headers={"X-User-Id": player_user},
    )
    assert player_get.status_code == 200
    player_traps = player_get.json()["traps"]
    assert len(player_traps) == 1
    assert player_traps[0]["name"] == "Visible Barricade"
    assert not any(t["is_secret"] for t in player_traps)

    # 6. DM queries traps -> receives all traps including secret pit
    dm_get = client.get(
        f"/api/v1/boards/{board_id}/traps?campaign_id={campaign_id}",
        headers={"X-User-Id": dm_user},
    )
    assert dm_get.status_code == 200
    dm_traps = dm_get.json()["traps"]
    assert len(dm_traps) == 2
    assert any(t["trap_id"] == trap_id for t in dm_traps)

    # 7. Disarming the trap via public endpoint
    disarm_res = client.post(
        f"/api/v1/boards/{board_id}/traps/{trap_id}/disarm",
        headers={"X-User-Id": dm_user},
    )
    assert disarm_res.status_code == 200
    assert disarm_res.json()["status"] == "disarmed"
