"""Blackbox tests for frontier settlement chartering and initial haven setup.

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
async def test_blackbox_charter_frontier_settlement(
    client: TestClient,
    spicedb: MockSpiceDBClient,
    mock_bus: MockAsyncRedis,
):
    """Scenario 1: Charter a communal haven and verify event-sourced creation."""
    officer_id = "officer_elena"
    camp_id = str(uuid4())

    world_res = client.post(
        "/api/v1/shared-worlds",
        json={"name": "Ironwood Reach", "frontier_region": "The Deep Woods"},
        headers={"x-user-id": officer_id},
    )
    assert world_res.status_code == 201
    world_id = world_res.json()["shared_world_id"]

    await spicedb.write_relationship("shared_world", world_id, "participant", "user", officer_id)
    await spicedb.write_relationship("campaign", camp_id, "player", "user", officer_id)

    charter_payload = {
        "name": "Haven of the Silver Stag",
        "shared_world_id": world_id,
        "settlement_type": "haven",
        "region": "The Deep Woods",
        "coordinates": {"x": 120.5, "y": 340.2},
        "founded_by_campaign_id": camp_id,
        "defense_rating": 12,
        "facilities": {"workshop": 1, "sanctum": 1, "fortifications": 1, "watchtower": 1},
        "metadata": {"biome": "ancient_forest", "water_source": "crystal_spring"},
    }

    res = client.post("/settlements", json=charter_payload, headers={"x-user-id": officer_id})
    assert res.status_code == 201, res.text
    data = res.json()
    sid = data["settlement_id"]
    assert data["name"] == "Haven of the Silver Stag"
    assert data["settlement_type"] == "haven"
    assert data["defense_rating"] == 12
    assert data["facilities"]["workshop"] == 1
    assert data["facilities"]["sanctum"] == 1
    assert data["contributing_campaigns"] == [camp_id]

    # Verify event published to Redis Stream
    assert_stream_events(mock_bus, "SettlementChartered")

    # Frontdoor query endpoint verification
    query_res = client.get(f"/settlements/{sid}", headers={"x-user-id": officer_id})
    assert query_res.status_code == 200
    q_data = query_res.json()
    assert q_data["settlement_id"] == sid
    assert q_data["name"] == "Haven of the Silver Stag"

    # API v1 prefix verification
    v1_res = client.get(f"/api/v1/settlements/{sid}", headers={"x-user-id": officer_id})
    assert v1_res.status_code == 200
    assert v1_res.json()["settlement_id"] == sid


@pytest.mark.asyncio
async def test_blackbox_query_nonexistent_settlement(client: TestClient):
    """Scenario 2: Querying a non-existent settlement returns 404."""
    random_id = str(uuid4())
    res = client.get(f"/settlements/{random_id}", headers={"x-user-id": "anyone"})
    assert res.status_code == 404
