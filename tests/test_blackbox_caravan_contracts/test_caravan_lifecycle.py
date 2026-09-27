"""Blackbox tests for caravan escort lifecycle, ambushes, and settlement economy fulfillment.

Governed by: ADR-0001, ADR-0006, ADR-0011, Hard Invariant 7.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.mock_redis import MockAsyncRedis

from .conftest import assert_stream_events


@pytest.mark.asyncio
async def test_blackbox_caravan_lifecycle_ambush_and_settlement_economy_fulfillment(
    client: TestClient,
    mock_bus: MockAsyncRedis,
    spicedb: MockSpiceDBClient,
):
    """Test Scenario 3: Full lifecycle, ambush outcome, reward escrow, and economic price modifier sync."""
    officer_id = "guild_officer_marrow"
    contractor_id = "captain_val"
    campaign_poster = str(uuid4())
    campaign_escort = str(uuid4())

    # 1. Establish shared world and campaigns
    world_res = client.post(
        "/api/v1/shared-worlds",
        json={"name": "Ashen Frontier"},
        headers={"x-user-id": officer_id},
    )
    world_id = world_res.json()["shared_world_id"]

    for camp, owner, name in [
        (campaign_poster, officer_id, "Provisions Guild"),
        (campaign_escort, contractor_id, "Val's Freeblades"),
    ]:
        await spicedb.write_relationship("campaign", camp, "owner", "user", owner)
        client.post(
            f"/api/v1/shared-worlds/{world_id}/campaigns",
            json={"campaign_id": camp, "party_name": name},
            headers={"x-user-id": officer_id},
        )
    await spicedb.write_relationship("shared_world", world_id, "trade", "user", contractor_id)

    # 2. Post contract
    post_res = client.post(
        f"/api/v1/shared-worlds/{world_id}/caravans/contracts",
        json={
            "origin_outpost": "Oakhaven",
            "destination_outpost": "Ironford",
            "cargo": {"medicinal_herbs": 40, "refined_iron": 20},
            "cargo_value": 600,
            "route_risk_level": "medium",
            "transit_stages": 2,
            "escort_collateral": 100,
            "reward_gold": 300,
            "reward_reputation": 20,
            "posted_by_campaign_id": campaign_poster,
        },
        headers={"x-user-id": officer_id},
    )
    assert post_res.status_code == 201
    contract_id = post_res.json()["contract"]["contract_id"]
    base_url = f"/api/v1/shared-worlds/{world_id}/caravans/contracts/{contract_id}"

    # 3. Accept contract
    accept_res = client.post(
        f"{base_url}/accept",
        json={
            "contractor_campaign_id": campaign_escort,
            "contractor_party_name": "Val's Freeblades",
        },
        headers={"x-user-id": contractor_id},
    )
    assert accept_res.status_code == 200

    # 4. Dispatch caravan
    dispatch_res = client.post(
        f"{base_url}/dispatch",
        json={"dispatched_by_campaign_id": campaign_escort},
        headers={"x-user-id": contractor_id},
    )
    assert dispatch_res.status_code == 200
    assert dispatch_res.json()["caravan_id"] and dispatch_res.json()["status"] == "in_transit"

    # 5. Report tactical ambush outcomes: Stage 1 repelled, Stage 2 cargo damaged (15% lost)
    for stage, a_type, danger, outcome, loss, notes in [
        (1, "goblin_archers", 2, "repelled", 0.0, "Ambush defeated."),
        (2, "hill_trolls", 3, "cargo_damaged", 0.15, "Supply wagon burned."),
    ]:
        ambush_res = client.post(
            f"{base_url}/ambush",
            json={
                "stage_index": stage,
                "ambush_type": a_type,
                "danger_level": danger,
                "outcome": outcome,
                "cargo_loss_percentage": loss,
                "reported_by_campaign_id": campaign_escort,
                "notes": notes,
            },
            headers={"x-user-id": contractor_id},
        )
        assert ambush_res.status_code == 200 and ambush_res.json()["ambush"]["outcome"] == outcome

    # 6. Fulfill contract upon arrival at destination outpost
    fulfill_res = client.post(f"{base_url}/fulfill", json={}, headers={"x-user-id": contractor_id})
    assert fulfill_res.status_code == 200
    data = fulfill_res.json()
    assert data["contract"]["status"] == "fulfilled"
    assert data["payout"]["status"] == "fulfilled"
    assert data["payout"]["cargo_delivered"] == {"medicinal_herbs": 34, "refined_iron": 17}
    assert data["payout"]["reward_gold_paid"] > 300  # base reward + collateral refund

    # 7. Check destination outpost economy sync via public REST frontdoor
    stock_res = client.get(
        f"/api/v1/shared-worlds/{world_id}/outposts/Ironford/merchant-stock",
        headers={"x-user-id": officer_id},
    )
    assert stock_res.status_code == 200
    stock = stock_res.json()["stock"]
    assert stock["workshop_reagents"] == {"medicinal_herbs": 34, "refined_iron": 17}
    assert stock["delivery_stats"]["successful_deliveries"] == 1
    assert "price_modifier" in stock

    # Verify CloudEvents emission over Redis Streams
    assert_stream_events(
        mock_bus,
        "CaravanContractPosted",
        "CaravanContractAccepted",
        "CaravanDispatched",
        "CaravanAmbushed",
        "CaravanTradeFulfilled",
    )
