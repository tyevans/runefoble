"""Blackbox tests for facility upgrading, fortification reinforcement, and rest boons.

Governed by ADR-0001, ADR-0006, ADR-0011, and Hard Invariant 7 (Blackbox TDD).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.mock_redis import MockAsyncRedis

from .conftest import assert_stream_events


@pytest.mark.asyncio
async def test_blackbox_upgrade_settlement_facilities(
    client: TestClient,
    spicedb: MockSpiceDBClient,
    mock_bus: MockAsyncRedis,
):
    """Test upgrading workshop and fortification facilities with event stream verification."""
    user_id = "builder_thorin"
    camp_a = str(uuid4())

    world_res = client.post(
        "/api/v1/shared-worlds",
        json={"name": "Crag Valley", "frontier_region": "Stonepeaks"},
        headers={"x-user-id": user_id},
    )
    world_id = world_res.json()["shared_world_id"]
    await spicedb.write_relationship("shared_world", world_id, "participant", "user", user_id)
    await spicedb.write_relationship("campaign", camp_a, "player", "user", user_id)

    # Charter settlement
    charter_res = client.post(
        "/settlements",
        json={
            "name": "High Crag Stronghold",
            "shared_world_id": world_id,
            "settlement_type": "fortress",
            "founded_by_campaign_id": camp_a,
            "defense_rating": 15,
        },
        headers={"x-user-id": user_id},
    )
    sid = charter_res.json()["settlement_id"]

    # Upgrade workshop
    up_res = client.post(
        f"/settlements/{sid}/upgrade",
        json={
            "facility_id": "workshop",
            "contributing_campaign_id": camp_a,
            "gold_spent": 200,
            "materials_spent": {"obsidian": 5, "mithril": 2},
        },
        headers={"x-user-id": user_id},
    )
    assert up_res.status_code == 200
    up_data = up_res.json()
    assert up_data["facilities"]["workshop"] == 2
    assert up_data["gold_invested"] == 200
    assert up_data["materials_treasury"]["obsidian"] == 5
    assert up_data["materials_treasury"]["mithril"] == 2

    # Upgrade fortifications -> improves defense
    fort_res = client.post(
        f"/settlements/{sid}/upgrade",
        json={
            "facility_id": "fortifications",
            "contributing_campaign_id": camp_a,
            "gold_spent": 100,
        },
        headers={"x-user-id": user_id},
    )
    assert fort_res.status_code == 200
    assert fort_res.json()["facilities"]["fortifications"] == 2
    assert fort_res.json()["defense_rating"] >= 20

    # Verify event publication
    assert_stream_events(mock_bus, "SettlementUpgraded")


@pytest.mark.asyncio
async def test_blackbox_claim_haven_rest_boon(
    client: TestClient,
    spicedb: MockSpiceDBClient,
    mock_bus: MockAsyncRedis,
):
    """Test claiming resting sanctum boons in a communal haven."""
    user_id = "cleric_seraphina"
    camp_id = str(uuid4())

    world_res = client.post(
        "/api/v1/shared-worlds",
        json={"name": "Verdant Reach", "frontier_region": "Sunken Delta"},
        headers={"x-user-id": user_id},
    )
    world_id = world_res.json()["shared_world_id"]
    await spicedb.write_relationship("shared_world", world_id, "participant", "user", user_id)
    await spicedb.write_relationship("campaign", camp_id, "player", "user", user_id)

    charter_res = client.post(
        "/settlements",
        json={
            "name": "Sanctuary of Light",
            "shared_world_id": world_id,
            "founded_by_campaign_id": camp_id,
        },
        headers={"x-user-id": user_id},
    )
    sid = charter_res.json()["settlement_id"]

    boon_res = client.post(
        f"/settlements/{sid}/claim-boon",
        json={"campaign_id": camp_id, "character_id": "char_123", "facility_id": "sanctum"},
        headers={"x-user-id": user_id},
    )
    assert boon_res.status_code == 200
    assert "Sanctuary Rest" in boon_res.json()["boon"]
    assert_stream_events(mock_bus, "SettlementRestBoonClaimed")
