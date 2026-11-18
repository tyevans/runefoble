"""Blackbox tests for cross-campaign contract acceptance and SpiceDB authorization.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object-Level Authorization
- ADR-0006: Redis Streams Event Bus
- Hard Invariant 7: Blackbox TDD with frontdoor setup
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.stream_events import assert_stream_events
from tests.helpers.ws_identity import SIGNING_ISSUER

from .conftest import create_campaign, join_campaign

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.mark.asyncio
async def test_blackbox_cross_campaign_acceptance_and_zanzibar_authorization(
    client: TestClient,
    mock_bus: MockAsyncRedis,
    spicedb: MockSpiceDBClient,
):
    """Test Scenario 2: Cross-campaign contract acceptance and SpiceDB Zanzibar role enforcement."""
    officer_id = "officer_lyra"
    grunt_user = "recruit_grunt"

    # Establish shared world
    world_res = client.post(
        "/api/v1/shared-worlds",
        json={"name": "Frontier Trade League"},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(officer_id)}"},
    )
    world_id = world_res.json()["shared_world_id"]

    # Registering a campaign needs guild officer and campaign owner, so the officer owns both.
    # grunt_user is a plain player of campaign B and has no run_session grant.
    campaign_a = create_campaign(client, officer_id)
    campaign_b = create_campaign(client, officer_id)
    join_campaign(client, campaign_b, officer_id, grunt_user)

    # Register campaign A and B

    client.post(
        f"/api/v1/shared-worlds/{world_id}/campaigns",
        json={"campaign_id": campaign_a, "party_name": "Guild Supply"},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(officer_id)}"},
    )
    client.post(
        f"/api/v1/shared-worlds/{world_id}/campaigns",
        json={"campaign_id": campaign_b, "party_name": "Iron Claws"},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(officer_id)}"},
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
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(officer_id)}"},
    )
    assert deadly_res.status_code == 201
    deadly_contract_id = deadly_res.json()["contract"]["contract_id"]

    # Grunt recruit attempts to accept deadly high-tier contract -> 403 Forbidden!
    unauth_accept = client.post(
        f"/api/v1/shared-worlds/{world_id}/caravans/contracts/{deadly_contract_id}/accept",
        json={"contractor_campaign_id": campaign_b, "contractor_party_name": "Iron Claws"},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(grunt_user)}"},
    )
    assert unauth_accept.status_code == 403
    assert "High-tier mercenary contracts require" in unauth_accept.text

    # The guild officer accepts the deadly contract for campaign B -> 200 OK!
    auth_accept = client.post(
        f"/api/v1/shared-worlds/{world_id}/caravans/contracts/{deadly_contract_id}/accept",
        json={"contractor_campaign_id": campaign_b, "contractor_party_name": "Iron Claws"},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(officer_id)}"},
    )
    assert auth_accept.status_code == 200
    assert auth_accept.json()["contract"]["status"] == "accepted"
    assert auth_accept.json()["contract"]["contractor_party_name"] == "Iron Claws"

    # Verify event published to Redis Stream
    assert_stream_events(mock_bus, "runefoble.events.west_marches.caravan_contract_accepted")
