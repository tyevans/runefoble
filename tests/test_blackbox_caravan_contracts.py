"""Frontdoor blackbox tests for Cross-Campaign Caravan Trading Ledgers & Mercenary Contracts.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object-Level Authorization
- ADR-0006: Redis Streams Event Bus
- ADR-0011: eventsource-py Core Event Sourcing
- ADR-0013: Microfrontend Architecture & Component Manifest
- PRD-0007 / US-0058: West Marches Shared World State & Cross-Campaign Trade
- Hard Invariant 7: Blackbox TDD with frontdoor setup (zero backdoor state manipulation)
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session.dependencies import (
    STREAM_WEST_MARCHES,
    set_event_bus,
    set_spicedb_client,
)
from game_session.main import app as session_app
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.mock_redis import MockAsyncRedis
from runefoble_platform.redis_bus import RedisStreamsEventBus


@pytest.fixture
def mock_bus():
    redis_client = MockAsyncRedis()
    bus = RedisStreamsEventBus(client=redis_client)
    set_event_bus(bus)
    yield redis_client
    set_event_bus(None)


@pytest.fixture
def client():
    mock_spicedb = MockSpiceDBClient()
    set_spicedb_client(mock_spicedb)
    return TestClient(session_app)


@pytest.mark.asyncio
async def test_blackbox_caravan_contract_posting_and_board_queries(
    client: TestClient,
    mock_bus: MockAsyncRedis,
):
    """Test Scenario 1: Posting contracts and filtering the notice board through frontdoor REST APIs."""
    officer_id = "guild_officer_rowan"
    campaign_a = str(uuid4())

    spicedb = MockSpiceDBClient()
    set_spicedb_client(spicedb)

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
    entries = mock_bus.streams.get(STREAM_WEST_MARCHES, [])
    assert any("CaravanContractPosted" in str(entry[1]) for entry in entries)

    # 3. Query notice board with filters
    # Filter by destination matching
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


@pytest.mark.asyncio
async def test_blackbox_cross_campaign_acceptance_and_zanzibar_authorization(
    client: TestClient,
    mock_bus: MockAsyncRedis,
):
    """Test Scenario 2: Cross-campaign contract acceptance and SpiceDB Zanzibar role enforcement."""
    officer_id = "officer_lyra"
    leader_b = "party_leader_b"
    grunt_user = "recruit_grunt"
    campaign_a = str(uuid4())
    campaign_b = str(uuid4())

    spicedb = MockSpiceDBClient()
    set_spicedb_client(spicedb)

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
    entries = mock_bus.streams.get(STREAM_WEST_MARCHES, [])
    assert any("CaravanContractAccepted" in str(entry[1]) for entry in entries)


@pytest.mark.asyncio
async def test_blackbox_caravan_lifecycle_ambush_and_settlement_economy_fulfillment(
    client: TestClient,
    mock_bus: MockAsyncRedis,
):
    """Test Scenario 3: Full lifecycle, ambush outcome, reward escrow, and economic price modifier sync."""
    officer_id = "guild_officer_marrow"
    contractor_id = "captain_val"
    campaign_poster = str(uuid4())
    campaign_escort = str(uuid4())

    spicedb = MockSpiceDBClient()
    set_spicedb_client(spicedb)

    # 1. Establish shared world and campaigns
    world_res = client.post(
        "/api/v1/shared-worlds",
        json={"name": "Ashen Frontier"},
        headers={"x-user-id": officer_id},
    )
    world_id = world_res.json()["shared_world_id"]

    await spicedb.write_relationship("campaign", campaign_poster, "owner", "user", officer_id)
    await spicedb.write_relationship("campaign", campaign_escort, "owner", "user", contractor_id)
    await spicedb.write_relationship("shared_world", world_id, "trade", "user", contractor_id)

    client.post(
        f"/api/v1/shared-worlds/{world_id}/campaigns",
        json={"campaign_id": campaign_poster, "party_name": "Provisions Guild"},
        headers={"x-user-id": officer_id},
    )
    client.post(
        f"/api/v1/shared-worlds/{world_id}/campaigns",
        json={"campaign_id": campaign_escort, "party_name": "Val's Freeblades"},
        headers={"x-user-id": officer_id},
    )

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

    # 3. Accept contract
    accept_res = client.post(
        f"/api/v1/shared-worlds/{world_id}/caravans/contracts/{contract_id}/accept",
        json={
            "contractor_campaign_id": campaign_escort,
            "contractor_party_name": "Val's Freeblades",
        },
        headers={"x-user-id": contractor_id},
    )
    assert accept_res.status_code == 200

    # 4. Dispatch caravan
    dispatch_res = client.post(
        f"/api/v1/shared-worlds/{world_id}/caravans/contracts/{contract_id}/dispatch",
        json={"dispatched_by_campaign_id": campaign_escort},
        headers={"x-user-id": contractor_id},
    )
    assert dispatch_res.status_code == 200
    assert dispatch_res.json()["caravan_id"]
    assert dispatch_res.json()["status"] == "in_transit"

    # 5. Report tactical ambush outcome: Stage 1 repelled
    ambush_res = client.post(
        f"/api/v1/shared-worlds/{world_id}/caravans/contracts/{contract_id}/ambush",
        json={
            "stage_index": 1,
            "ambush_type": "goblin_archers",
            "danger_level": 2,
            "outcome": "repelled",
            "cargo_loss_percentage": 0.0,
            "reported_by_campaign_id": campaign_escort,
            "notes": "Ambush defeated with zero casualties.",
        },
        headers={"x-user-id": contractor_id},
    )
    assert ambush_res.status_code == 200
    assert ambush_res.json()["ambush"]["outcome"] == "repelled"
    assert ambush_res.json()["status"] == "in_transit"

    # 6. Report tactical ambush outcome: Stage 2 cargo damaged (15% lost)
    ambush_res_2 = client.post(
        f"/api/v1/shared-worlds/{world_id}/caravans/contracts/{contract_id}/ambush",
        json={
            "stage_index": 2,
            "ambush_type": "hill_trolls",
            "danger_level": 3,
            "outcome": "cargo_damaged",
            "cargo_loss_percentage": 0.15,
            "reported_by_campaign_id": campaign_escort,
            "notes": "One supply wagon burned by troll torches.",
        },
        headers={"x-user-id": contractor_id},
    )
    assert ambush_res_2.status_code == 200
    assert ambush_res_2.json()["ambush"]["outcome"] == "cargo_damaged"

    # 7. Fulfill contract upon arrival at destination outpost
    fulfill_res = client.post(
        f"/api/v1/shared-worlds/{world_id}/caravans/contracts/{contract_id}/fulfill",
        json={},
        headers={"x-user-id": contractor_id},
    )
    assert fulfill_res.status_code == 200
    fulfill_data = fulfill_res.json()
    assert fulfill_data["contract"]["status"] == "fulfilled"

    # Verify payout calculations: collateral refunded + proportional gold and reputation
    payout = fulfill_data["payout"]
    assert payout["status"] == "fulfilled"
    assert payout["cargo_delivered"]["medicinal_herbs"] == 34  # 40 * 0.85 = 34
    assert payout["cargo_delivered"]["refined_iron"] == 17  # 20 * 0.85 = 17
    assert payout["reward_gold_paid"] > 300  # base reward + collateral refund

    # 8. Check destination outpost economy sync via public REST frontdoor
    stock_res = client.get(
        f"/api/v1/shared-worlds/{world_id}/outposts/Ironford/merchant-stock",
        headers={"x-user-id": officer_id},
    )
    assert stock_res.status_code == 200
    stock = stock_res.json()["stock"]
    assert "workshop_reagents" in stock
    assert stock["workshop_reagents"]["medicinal_herbs"] == 34
    assert stock["workshop_reagents"]["refined_iron"] == 17
    assert stock["delivery_stats"]["successful_deliveries"] == 1
    assert "price_modifier" in stock

    # Verify CloudEvents emission over Redis Streams
    entries = mock_bus.streams.get(STREAM_WEST_MARCHES, [])
    assert any("CaravanContractPosted" in str(entry[1]) for entry in entries)
    assert any("CaravanContractAccepted" in str(entry[1]) for entry in entries)
    assert any("CaravanDispatched" in str(entry[1]) for entry in entries)
    assert any("CaravanAmbushed" in str(entry[1]) for entry in entries)
    assert any("CaravanTradeFulfilled" in str(entry[1]) for entry in entries)


@pytest.mark.asyncio
async def test_blackbox_caravan_destroyed_and_ui_manifest(
    client: TestClient,
    mock_bus: MockAsyncRedis,
):
    """Test Scenario 4: Catastrophic caravan destruction and UI microfrontend registration."""
    officer_id = "officer_dane"
    contractor_id = "ranger_thorn"
    campaign_id = str(uuid4())

    spicedb = MockSpiceDBClient()
    set_spicedb_client(spicedb)

    world_res = client.post(
        "/api/v1/shared-worlds",
        json={"name": "Perilous Range"},
        headers={"x-user-id": officer_id},
    )
    world_id = world_res.json()["shared_world_id"]

    await spicedb.write_relationship("campaign", campaign_id, "owner", "user", officer_id)
    await spicedb.write_relationship("campaign", campaign_id, "owner", "user", contractor_id)
    await spicedb.write_relationship("shared_world", world_id, "trade", "user", contractor_id)

    client.post(
        f"/api/v1/shared-worlds/{world_id}/campaigns",
        json={"campaign_id": campaign_id, "party_name": "Ranger Corps"},
        headers={"x-user-id": officer_id},
    )

    # Post, accept, and dispatch
    post_res = client.post(
        f"/api/v1/shared-worlds/{world_id}/caravans/contracts",
        json={
            "origin_outpost": "HighlandKeep",
            "destination_outpost": "Shadowfen",
            "cargo": {"potions": 10},
            "cargo_value": 500,
            "route_risk_level": "high",
            "transit_stages": 2,
            "reward_gold": 250,
            "posted_by_campaign_id": campaign_id,
        },
        headers={"x-user-id": officer_id},
    )
    cid = post_res.json()["contract"]["contract_id"]

    client.post(
        f"/api/v1/shared-worlds/{world_id}/caravans/contracts/{cid}/accept",
        json={"contractor_campaign_id": campaign_id, "contractor_party_name": "Ranger Corps"},
        headers={"x-user-id": contractor_id},
    )
    client.post(
        f"/api/v1/shared-worlds/{world_id}/caravans/contracts/{cid}/dispatch",
        json={},
        headers={"x-user-id": contractor_id},
    )

    # Report catastrophic ambush: caravan destroyed
    ambush_res = client.post(
        f"/api/v1/shared-worlds/{world_id}/caravans/contracts/{cid}/ambush",
        json={
            "stage_index": 1,
            "ambush_type": "red_dragon",
            "danger_level": 5,
            "outcome": "caravan_destroyed",
            "cargo_loss_percentage": 1.0,
            "notes": "Red dragon incinerated the entire caravan.",
        },
        headers={"x-user-id": contractor_id},
    )
    assert ambush_res.status_code == 200
    assert ambush_res.json()["status"] == "failed"

    # Attempting to fulfill a destroyed contract must fail
    fail_res = client.post(
        f"/api/v1/shared-worlds/{world_id}/caravans/contracts/{cid}/fulfill",
        json={},
        headers={"x-user-id": contractor_id},
    )
    assert fail_res.status_code == 400

    # Verify UI microfrontend manifest advertises runefoble-caravan-board
    ui_manifest_res = client.get("/ui/manifest")
    assert ui_manifest_res.status_code == 200
    manifest = ui_manifest_res.json()
    assert "runefoble-caravan-board" in manifest["components"]
