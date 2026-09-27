"""Blackbox tests for cross-campaign contract acceptance and SpiceDB authorization.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object-Level Authorization
- ADR-0006: Redis Streams Event Bus
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
async def test_blackbox_cross_campaign_acceptance_and_zanzibar_authorization(
    client: TestClient,
    mock_bus: MockAsyncRedis,
    spicedb: MockSpiceDBClient,
):
    """Test Scenario 2: Cross-campaign contract acceptance and SpiceDB Zanzibar role enforcement."""
    officer_id = "officer_lyra"
    leader_b = "party_leader_b"
    grunt_user = "recruit_grunt"
    campaign_a = str(uuid4())
    campaign_b = str(uuid4())

    # Establish shared world
    world_res = client.post(
        "/api/v1/shared-worlds",
        json={"name": "Frontier Trade League"},
        headers={"x-user-id": officer_id},
    )
    world_id = world_res.json()["shared_world_id"]

    # Register campaign A and B
    await spicedb.write_relationship("campaign", campaign_a, "owner", "user", officer_id)
    await spicedb.write_relationship("campaign", campaign_b, "owner", "user", leader_b)
    await spicedb.write_relationship("campaign", campaign_b, "player", "user", grunt_user)
    await spicedb.write_relationship("shared_world", world_id, "participant", "user", grunt_user)

    client.post(
        f"/api/v1/shared-worlds/{world_id}/campaigns",
        json={"campaign_id": campaign_a, "party_name": "Guild Supply"},
        headers={"x-user-id": officer_id},
    )
    client.post(
        f"/api/v1/shared-worlds/{world_id}/campaigns",
        json={"campaign_id": campaign_b, "party_name": "Iron Claws"},
        headers={"x-user-id": officer_id},
    )

    # Post a high-tier ("deadly") contract
    deadly_res = client.post(
        f"/api/v1/shared-worlds/{world_id}/caravans/contracts",
        json={
            "origin_outpost": "Ironford",
            "destination_outpost": "Shadowfen",
            "cargo": {"dragon_scales": 5},
            "cargo_value": 2000,
            "route_risk_level": "deadly",
            "transit_stages": 3,
            "escort_collateral": 300,
            "reward_gold": 1200,
            "reward_reputation": 50,
            "posted_by_campaign_id": campaign_a,
        },
        headers={"x-user-id": officer_id},
    )
    assert deadly_res.status_code == 201
    deadly_contract_id = deadly_res.json()["contract"]["contract_id"]

    # Grunt recruit attempts to accept deadly high-tier contract -> 403 Forbidden!
    unauth_accept = client.post(
        f"/api/v1/shared-worlds/{world_id}/caravans/contracts/{deadly_contract_id}/accept",
        json={"contractor_campaign_id": campaign_b, "contractor_party_name": "Iron Claws"},
        headers={"x-user-id": grunt_user},
    )
    assert unauth_accept.status_code == 403
    assert "High-tier mercenary contracts require" in unauth_accept.text

    # Party leader B accepts deadly contract -> 200 OK!
    auth_accept = client.post(
        f"/api/v1/shared-worlds/{world_id}/caravans/contracts/{deadly_contract_id}/accept",
        json={"contractor_campaign_id": campaign_b, "contractor_party_name": "Iron Claws"},
        headers={"x-user-id": leader_b},
    )
    assert auth_accept.status_code == 200
    assert auth_accept.json()["contract"]["status"] == "accepted"
    assert auth_accept.json()["contract"]["contractor_party_name"] == "Iron Claws"

    # Verify event published to Redis Stream
    assert_stream_events(mock_bus, "CaravanContractAccepted")
