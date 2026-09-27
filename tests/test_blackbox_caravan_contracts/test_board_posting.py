"""Blackbox tests for caravan trade contract posting and notice board queries.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object-Level Authorization
- ADR-0006: Redis Streams Event Bus
- ADR-0011: eventsource-py Core Event Sourcing
- Hard Invariant 7: Blackbox TDD with frontdoor setup
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.mock_redis import MockAsyncRedis

from .conftest import assert_stream_events


@pytest.mark.asyncio
async def test_blackbox_caravan_contract_posting_and_board_queries(
    client: TestClient,
    mock_bus: MockAsyncRedis,
    spicedb: MockSpiceDBClient,
):
    """Test Scenario 1: Posting contracts and filtering the notice board through frontdoor REST APIs."""
    officer_id = "guild_officer_rowan"
    campaign_a = str(uuid4())

    # 1. Establish shared frontier world
    world_res = client.post(
        "/api/v1/shared-worlds",
        json={
            "name": "The Sunken Marches",
            "frontier_region": "The Shadowed Wilds",
            "description": "Frontier trading and exploration ledger.",
        },
        headers={"x-user-id": officer_id},
    )
    assert world_res.status_code == 201, world_res.text
    world_id = world_res.json()["shared_world_id"]

    # Register campaign A
    await spicedb.write_relationship("campaign", campaign_a, "owner", "user", officer_id)
    reg_res = client.post(
        f"/api/v1/shared-worlds/{world_id}/campaigns",
        json={"campaign_id": campaign_a, "party_name": "The Amber Vanguard"},
        headers={"x-user-id": officer_id},
    )
    assert reg_res.status_code == 201

    # 2. Post a caravan trade contract via public HTTP endpoint
    post_res = client.post(
        f"/api/v1/shared-worlds/{world_id}/caravans/contracts",
        json={
            "origin_outpost": "Bastion Cross",
            "destination_outpost": "Ironford",
            "cargo": {"iron_ingots": 50, "timber": 25},
            "cargo_value": 400,
            "route_risk_level": "medium",
            "transit_stages": 2,
            "escort_collateral": 60,
            "reward_gold": 220,
            "reward_reputation": 15,
            "posted_by_campaign_id": campaign_a,
            "expires_in_turns": 12,
        },
        headers={"x-user-id": officer_id},
    )
    assert post_res.status_code == 201, post_res.text
    contract_data = post_res.json()["contract"]
    contract_id = contract_data["contract_id"]
    assert contract_data["origin_outpost"] == "Bastion Cross"
    assert contract_data["destination_outpost"] == "Ironford"
    assert contract_data["status"] == "open"
    assert contract_data["reward_gold"] == 220

    # Verify event published to Redis Stream
    assert_stream_events(mock_bus, "CaravanContractPosted")

    # 3. Query notice board with filters
    board_res = client.get(
        f"/api/v1/shared-worlds/{world_id}/caravans/contracts?destination=Ironford",
        headers={"x-user-id": officer_id},
    )
    assert board_res.status_code == 200
    contracts = board_res.json()["contracts"]
    assert len(contracts) == 1
    assert contracts[0]["contract_id"] == contract_id

    # Filter by destination non-matching
    board_empty = client.get(
        f"/api/v1/shared-worlds/{world_id}/caravans/contracts?destination=HighlandKeep",
        headers={"x-user-id": officer_id},
    )
    assert board_empty.status_code == 200
    assert len(board_empty.json()["contracts"]) == 0

    # Filter by risk level
    board_risk = client.get(
        f"/api/v1/shared-worlds/{world_id}/caravans/contracts?risk_level=medium",
        headers={"x-user-id": officer_id},
    )
    assert board_risk.status_code == 200
    assert len(board_risk.json()["contracts"]) == 1

    # Filter by status
    board_status = client.get(
        f"/api/v1/shared-worlds/{world_id}/caravans/contracts?status=open",
        headers={"x-user-id": officer_id},
    )
    assert board_status.status_code == 200
    assert len(board_status.json()["contracts"]) == 1

    # Fetch individual contract
    get_res = client.get(
        f"/api/v1/shared-worlds/{world_id}/caravans/contracts/{contract_id}",
        headers={"x-user-id": officer_id},
    )
    assert get_res.status_code == 200
    assert get_res.json()["contract"]["contract_id"] == contract_id
