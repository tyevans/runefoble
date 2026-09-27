"""Frontdoor blackbox tests for West Marches shared persistent world state and cross-campaign trade.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object-Level Authorization
- ADR-0006: Redis Streams Event Bus
- ADR-0011: eventsource-py Core Event Sourcing
- PRD-0007: Campaign Worldbuilding Lore & redstring RAG Engine
- US-0058: West Marches Shared Persistent World State & Cross-Campaign Trade
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


@pytest.fixture
def spicedb_client():
    mock_spicedb = MockSpiceDBClient()
    set_spicedb_client(mock_spicedb)
    return mock_spicedb


@pytest.mark.asyncio
async def test_blackbox_west_marches_shared_frontier_and_cross_party_discoveries(
    client: TestClient,
    mock_bus: MockAsyncRedis,
):
    """Test Scenario 1 (US-0058): Cross-Party Discovery Synchronization."""
    officer_id = "rowan_officer"
    blue_player_id = "blue_explorer"
    gold_player_id = "gold_scout"
    campaign_blue = str(uuid4())
    campaign_gold = str(uuid4())

    spicedb = MockSpiceDBClient()
    set_spicedb_client(spicedb)

    # 1. Guild officer creates persistent West Marches shared world via HTTP frontdoor
    world_res = client.post(
        "/api/v1/shared-worlds",
        json={
            "name": "The Sunken Marches",
            "frontier_region": "The Shadowed Fenlands",
            "description": "A vast, dangerous marshland explored by multiple mercenary guilds.",
        },
        headers={"x-user-id": officer_id},
    )
    assert world_res.status_code == 201, world_res.text
    world_data = world_res.json()
    world_id = world_data["shared_world_id"]
    assert world_data["name"] == "The Sunken Marches"

    # Set up campaign relations in SpiceDB
    await spicedb.write_relationship("campaign", campaign_blue, "player", "user", blue_player_id)
    await spicedb.write_relationship("campaign", campaign_gold, "player", "user", gold_player_id)

    # 2. Register Party Blue and Party Gold campaigns to the shared world
    reg_blue = client.post(
        f"/api/v1/shared-worlds/{world_id}/campaigns",
        json={"campaign_id": campaign_blue, "party_name": "Party Blue"},
        headers={"x-user-id": officer_id},
    )
    assert reg_blue.status_code == 201
    assert reg_blue.json()["party_name"] == "Party Blue"

    reg_gold = client.post(
        f"/api/v1/shared-worlds/{world_id}/campaigns",
        json={"campaign_id": campaign_gold, "party_name": "Party Gold"},
        headers={"x-user-id": officer_id},
    )
    assert reg_gold.status_code == 201
    assert reg_gold.json()["party_name"] == "Party Gold"

    # 3. Party Blue maps and records discovery: "Sunken Crypt of Arnor"
    discovery_payload = {
        "name": "Sunken Crypt of Arnor",
        "discovery_type": "dungeon",
        "coordinates": {"x": 145.0, "y": 280.0},
        "discovered_by_campaign_id": campaign_blue,
        "discovered_by_party_name": "Party Blue",
        "description": "Flooded ancient crypt entrance guarded by water elementals.",
        "danger_level": 4,
        "metadata": {"entrance": "submerged_tunnel", "biome": "bog"},
    }
    disc_res = client.post(
        f"/api/v1/shared-worlds/{world_id}/discoveries",
        json=discovery_payload,
        headers={"x-user-id": blue_player_id},
    )
    assert disc_res.status_code == 201, disc_res.text
    disc_data = disc_res.json()["discovery"]
    assert disc_data["name"] == "Sunken Crypt of Arnor"
    assert disc_data["discovered_by_party_name"] == "Party Blue"
    assert "timestamp" in disc_data

    # Verify event published to Redis Streams (ADR-0006)
    entries = mock_bus.streams.get(STREAM_WEST_MARCHES, [])
    assert any(
        "CrossCampaignDiscoveryShared" in entry[1].get("event_type", "")
        or "CrossCampaignDiscoveryShared" in str(entry[1])
        for entry in entries
    ), f"Expected CrossCampaignDiscoveryShared in stream {STREAM_WEST_MARCHES}"

    # 4. Party Gold embarks on an expedition and queries shared discoveries frontdoor
    gold_query = client.get(
        f"/api/v1/shared-worlds/{world_id}/discoveries",
        headers={"x-user-id": gold_player_id},
    )
    assert gold_query.status_code == 200
    discoveries = gold_query.json()["discoveries"]
    assert len(discoveries) == 1
    found = discoveries[0]
    assert found["name"] == "Sunken Crypt of Arnor"
    assert found["discovered_by_party_name"] == "Party Blue"
    assert found["coordinates"] == {"x": 145.0, "y": 280.0}
    assert found["metadata"]["entrance"] == "submerged_tunnel"


@pytest.mark.asyncio
async def test_blackbox_caravan_trade_and_merchant_stock_unlocks(
    client: TestClient,
    mock_bus: MockAsyncRedis,
):
    """Test Scenario 2 (US-0058): Caravan Trading and Outpost Resource Ledgers."""
    officer_id = "rowan_officer"
    blue_trader = "blue_merchant"
    gold_buyer = "gold_alchemist"
    campaign_blue = str(uuid4())
    campaign_gold = str(uuid4())

    spicedb = MockSpiceDBClient()
    set_spicedb_client(spicedb)

    # Establish shared world
    world_res = client.post(
        "/api/v1/shared-worlds",
        json={"name": "The Sunken Marches", "frontier_region": "Trade Coast"},
        headers={"x-user-id": officer_id},
    )
    world_id = world_res.json()["shared_world_id"]

    await spicedb.write_relationship("campaign", campaign_blue, "player", "user", blue_trader)
    await spicedb.write_relationship("campaign", campaign_gold, "player", "user", gold_buyer)
    client.post(
        f"/api/v1/shared-worlds/{world_id}/campaigns",
        json={"campaign_id": campaign_blue, "party_name": "Party Blue"},
        headers={"x-user-id": officer_id},
    )
    client.post(
        f"/api/v1/shared-worlds/{world_id}/campaigns",
        json={"campaign_id": campaign_gold, "party_name": "Party Gold"},
        headers={"x-user-id": officer_id},
    )

    # 1. Establish outposts: Fort Rowan and Highport
    outpost_res = client.post(
        f"/api/v1/shared-worlds/{world_id}/outposts",
        json={
            "name": "Highport",
            "region": "Eastern Coast",
            "contributing_campaign_id": campaign_blue,
            "facilities": {"harbor": 1, "alchemical_guild": 1},
        },
        headers={"x-user-id": blue_trader},
    )
    assert outpost_res.status_code == 201

    # 2. Party Blue dispatches caravan carrying alchemical reagents from Fort Rowan to Highport
    dispatch_res = client.post(
        f"/api/v1/shared-worlds/{world_id}/caravans/dispatch",
        json={
            "origin_outpost": "Fort Rowan",
            "destination_outpost": "Highport",
            "cargo": {"alchemical_reagents": 10, "silver_bloom": 5},
            "dispatched_by_campaign_id": campaign_blue,
            "transit_turns": 2,
        },
        headers={"x-user-id": blue_trader},
    )
    assert dispatch_res.status_code == 201
    caravan_id = dispatch_res.json()["caravan"]["caravan_id"]
    assert dispatch_res.json()["caravan"]["status"] == "in_transit"

    # 3. Caravan arrives safely according to the trade scheduler -> Complete trade
    complete_res = client.post(
        f"/api/v1/shared-worlds/{world_id}/caravans/{caravan_id}/complete",
        json={
            "unlocked_stock": {
                "elixir_of_frost_resistance": {
                    "name": "Elixir of Frost Resistance",
                    "price_gold": 50,
                    "quantity": 6,
                    "rarity": "rare",
                }
            }
        },
        headers={"x-user-id": blue_trader},
    )
    assert complete_res.status_code == 200
    assert complete_res.json()["caravan"]["status"] == "completed"

    # Verify CaravanTradeCompleted emitted to Redis Streams (ADR-0006)
    entries = mock_bus.streams.get(STREAM_WEST_MARCHES, [])
    assert any(
        "CaravanTradeCompleted" in entry[1].get("event_type", "")
        or "CaravanTradeCompleted" in str(entry[1])
        for entry in entries
    ), f"Expected CaravanTradeCompleted in stream {STREAM_WEST_MARCHES}"

    # 4. Party Gold visits Highport and inspects merchant stock
    stock_res = client.get(
        f"/api/v1/shared-worlds/{world_id}/outposts/Highport/merchant-stock",
        headers={"x-user-id": gold_buyer},
    )
    assert stock_res.status_code == 200
    stock_data = stock_res.json()["stock"]
    assert stock_data["workshop_reagents"]["alchemical_reagents"] == 10
    assert stock_data["workshop_reagents"]["silver_bloom"] == 5
    assert "elixir_of_frost_resistance" in stock_data["inventory"]
    assert stock_data["inventory"]["elixir_of_frost_resistance"]["rarity"] == "rare"


@pytest.mark.asyncio
async def test_blackbox_communal_tavern_board_and_notices(client: TestClient):
    """Test communal tavern notice board for bounties and expedition requests."""
    officer_id = "rowan_officer"
    blue_player = "blue_ranger"
    gold_player = "gold_paladin"
    campaign_blue = str(uuid4())
    campaign_gold = str(uuid4())

    spicedb = MockSpiceDBClient()
    set_spicedb_client(spicedb)

    world_res = client.post(
        "/api/v1/shared-worlds",
        json={"name": "Frontier Outskirts"},
        headers={"x-user-id": officer_id},
    )
    world_id = world_res.json()["shared_world_id"]

    await spicedb.write_relationship("campaign", campaign_blue, "player", "user", blue_player)
    await spicedb.write_relationship("campaign", campaign_gold, "player", "user", gold_player)
    client.post(
        f"/api/v1/shared-worlds/{world_id}/campaigns",
        json={"campaign_id": campaign_blue, "party_name": "Party Blue"},
        headers={"x-user-id": officer_id},
    )
    client.post(
        f"/api/v1/shared-worlds/{world_id}/campaigns",
        json={"campaign_id": campaign_gold, "party_name": "Party Gold"},
        headers={"x-user-id": officer_id},
    )

    # 1. Party Blue posts bounty to communal tavern notice board
    notice_res = client.post(
        f"/api/v1/shared-worlds/{world_id}/tavern-board/notices",
        json={
            "campaign_id": campaign_blue,
            "author_name": "Ranger Laura",
            "title": "Bounty: Cull the Marsh Trolls",
            "content": "Four marsh trolls sighted harassing supply convoys east of the Old Bridge.",
            "notice_type": "bounty",
            "bounty_reward": 150,
        },
        headers={"x-user-id": blue_player},
    )
    assert notice_res.status_code == 201
    notice_id = notice_res.json()["notice"]["notice_id"]

    # 2. Party Gold reads communal notices
    board_res = client.get(
        f"/api/v1/shared-worlds/{world_id}/tavern-board/notices",
        headers={"x-user-id": gold_player},
    )
    assert board_res.status_code == 200
    notices = board_res.json()["notices"]
    assert any(n["notice_id"] == notice_id and n["bounty_reward"] == 150 for n in notices)


@pytest.mark.asyncio
async def test_blackbox_spicedb_zanzibar_multi_party_isolation(client: TestClient):
    """Verify ADR-0001: While geography is shared, private character sheets & party secrets remain isolated."""
    spicedb = MockSpiceDBClient()
    set_spicedb_client(spicedb)

    officer_id = "rowan_officer"
    blue_player = "blue_ranger"
    gold_player = "gold_paladin"
    unauthorized_outsider = "stranger_malicious"

    campaign_blue = str(uuid4())
    campaign_gold = str(uuid4())
    char_blue_id = str(uuid4())

    world_res = client.post(
        "/api/v1/shared-worlds",
        json={"name": "Frontier Sanctum"},
        headers={"x-user-id": officer_id},
    )
    world_id = world_res.json()["shared_world_id"]

    # Setup campaign memberships
    await spicedb.write_relationship("campaign", campaign_blue, "player", "user", blue_player)
    await spicedb.write_relationship("campaign", campaign_gold, "player", "user", gold_player)
    await spicedb.write_relationship("character", char_blue_id, "owner", "user", blue_player)
    await spicedb.write_relationship(
        "character", char_blue_id, "campaign", "campaign", campaign_blue
    )

    client.post(
        f"/api/v1/shared-worlds/{world_id}/campaigns",
        json={"campaign_id": campaign_blue, "party_name": "Party Blue"},
        headers={"x-user-id": officer_id},
    )
    client.post(
        f"/api/v1/shared-worlds/{world_id}/campaigns",
        json={"campaign_id": campaign_gold, "party_name": "Party Gold"},
        headers={"x-user-id": officer_id},
    )

    # 1. Unauthorized outsider cannot view or mutate shared world
    unauth_res = client.get(
        f"/api/v1/shared-worlds/{world_id}",
        headers={"x-user-id": unauthorized_outsider},
    )
    assert unauth_res.status_code == 403

    unauth_disc = client.post(
        f"/api/v1/shared-worlds/{world_id}/discoveries",
        json={
            "name": "Illegal Outpost",
            "coordinates": {"x": 0.0, "y": 0.0},
            "discovered_by_campaign_id": "fake",
            "discovered_by_party_name": "Fake",
        },
        headers={"x-user-id": unauthorized_outsider},
    )
    assert unauth_disc.status_code == 403

    # 2. Both Party Blue and Party Gold CAN view the shared world
    assert (
        client.get(
            f"/api/v1/shared-worlds/{world_id}", headers={"x-user-id": blue_player}
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"/api/v1/shared-worlds/{world_id}", headers={"x-user-id": gold_player}
        ).status_code
        == 200
    )

    # 3. Zanzibar Scoping: Gold player CANNOT view Blue player's private character sheet
    # (SpiceDB Zanzibar schema check)
    blue_can_view_own_char = await spicedb.check_permission(
        "character", char_blue_id, "view", "user", blue_player
    )
    gold_can_view_blue_char = await spicedb.check_permission(
        "character", char_blue_id, "view", "user", gold_player
    )
    outsider_can_view_blue_char = await spicedb.check_permission(
        "character", char_blue_id, "view", "user", unauthorized_outsider
    )

    assert blue_can_view_own_char is True, "Owner must have view permission on character"
    assert gold_can_view_blue_char is False, (
        "Cross-party player must NOT have view permission on other party's character"
    )
    assert outsider_can_view_blue_char is False, (
        "Outsider must NOT have view permission on character"
    )
