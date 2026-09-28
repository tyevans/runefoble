"""Blackbox tests for settlement haven builder and establishment aggregate domain model.

Governed by ADR-0001, ADR-0002, ADR-0007, ADR-0011, and Hard Invariant 7 (Blackbox TDD).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session.dependencies import set_event_bus, set_spicedb_client
from game_session.main import app
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_events.settlements import (
    EstablishmentConstructedEvent,
    EstablishmentUpgradedEvent,
    SettlementFoundedEvent,
    SettlementTierUpgradedEvent,
)
from runefoble_platform.mock_redis import MockAsyncRedis
from runefoble_platform.redis_bus import RedisStreamsEventBus


@pytest.fixture
def mock_bus() -> MockAsyncRedis:
    bus_client = MockAsyncRedis()
    set_event_bus(RedisStreamsEventBus(client=bus_client))
    yield bus_client
    set_event_bus(None)


@pytest.fixture
def spicedb() -> MockSpiceDBClient:
    db = MockSpiceDBClient()
    set_spicedb_client(db)
    yield db
    set_spicedb_client(None)


@pytest.fixture
def client(spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis) -> TestClient:
    return TestClient(app)


def assert_event_emitted(mock_bus: MockAsyncRedis, event_name: str) -> None:
    """Verify that an event matching the given name was published to Redis streams."""
    entries = mock_bus.streams.get("runefoble.events.west_marches", [])
    ev_norm = event_name.lower().replace("_", "")
    assert any(ev_norm in str(entry[1]).lower().replace("_", "") for entry in entries), (
        f"Expected event '{event_name}' in stream, but found: {entries}"
    )


@pytest.mark.asyncio
async def test_blackbox_found_settlement_and_construct_establishment(
    client: TestClient, spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
) -> None:
    """Found a settlement haven and construct an establishment in a zoned district."""
    campaign_id = str(uuid4())
    mayor_user_id = f"mayor_{uuid4().hex[:8]}"

    # Frontdoor authorization: grant mayor 'play' on campaign
    await spicedb.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="player",
        subject_type="user",
        subject_id=mayor_user_id,
    )

    # 1. Found settlement via HTTP POST
    found_payload = {
        "name": "Oakhaven",
        "scale": "village",
        "biome": "river_confluence",
        "coordinates": {"x": 145.0, "y": 280.5},
        "prosperity": 150,
        "districts": ["commons", "agricultural_commons", "defensive_palisade"],
        "metadata": {"founder_title": "Mayor"},
    }
    found_res = client.post(
        f"/api/v1/campaigns/{campaign_id}/settlements",
        json=found_payload,
        headers={"x-user-id": mayor_user_id},
    )
    assert found_res.status_code == 201, found_res.text
    settlement_data = found_res.json()
    sid = settlement_data["settlement_id"]

    assert settlement_data["name"] == "Oakhaven"
    assert settlement_data["scale"] == "village"
    assert settlement_data["tier"] == 2
    assert settlement_data["biome"] == "river_confluence"
    assert "agricultural_commons" in settlement_data["districts"]
    assert settlement_data["prosperity"] == 150

    # Verify SettlementFounded domain event emitted
    assert_event_emitted(mock_bus, "SettlementFounded")

    # Verify CloudEvents compliance of SettlementFoundedEvent
    cloud_event = SettlementFoundedEvent(
        settlement_id=sid,
        campaign_id=campaign_id,
        name="Oakhaven",
        scale="village",
        biome="river_confluence",
    ).to_cloudevent_dict()
    assert cloud_event["specversion"] == "1.0"
    assert "settlement_founded" in cloud_event["type"]

    # 2. Construct establishment via HTTP POST
    construct_payload = {
        "district_id": "agricultural_commons",
        "category": "commerce",
        "name": "The Warm Hearth Bakery",
        "tier": 1,
        "capacity": 20,
        "operating_cost": 6,
        "amenities": ["brick_oven", "flour_mill"],
        "metadata": {"specialty": "honey_bread"},
    }
    est_res = client.post(
        f"/api/v1/settlements/{sid}/establishments",
        json=construct_payload,
        headers={"x-user-id": mayor_user_id},
    )
    assert est_res.status_code == 201, est_res.text
    est_data = est_res.json()
    eid = est_data["establishment_id"]

    assert est_data["settlement_id"] == sid
    assert est_data["district_id"] == "agricultural_commons"
    assert est_data["category"] == "commerce"
    assert est_data["name"] == "The Warm Hearth Bakery"
    assert est_data["capacity"] == 20
    assert "brick_oven" in est_data["amenities"]

    # Verify EstablishmentConstructed domain event emitted
    assert_event_emitted(mock_bus, "EstablishmentConstructed")

    # Verify CloudEvents compliance of EstablishmentConstructedEvent
    est_cloud_event = EstablishmentConstructedEvent(
        establishment_id=eid,
        settlement_id=sid,
        district_id="agricultural_commons",
        category="commerce",
        name="The Warm Hearth Bakery",
    ).to_cloudevent_dict()
    assert est_cloud_event["specversion"] == "1.0"
    assert "establishment_constructed" in est_cloud_event["type"]

    # 3. Query settlement projection and verify establishment linkage
    proj_res = client.get(
        f"/api/v1/campaigns/{campaign_id}/settlements/{sid}",
        headers={"x-user-id": mayor_user_id},
    )
    assert proj_res.status_code == 200, proj_res.text
    proj_data = proj_res.json()

    assert proj_data["settlement_id"] == sid
    assert len(proj_data["establishments"]) == 1
    linked_est = proj_data["establishments"][0]
    assert linked_est["establishment_id"] == eid
    assert linked_est["district_id"] == "agricultural_commons"
    assert linked_est["name"] == "The Warm Hearth Bakery"


@pytest.mark.asyncio
async def test_blackbox_settlement_scale_upgrade_and_prosperity_gate(
    client: TestClient, spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
) -> None:
    """Verify settlement tier upgrades, prosperity validation, and district expansion."""
    campaign_id = str(uuid4())
    mayor_id = f"mayor_{uuid4().hex[:8]}"

    await spicedb.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="dungeon_master",
        subject_type="user",
        subject_id=mayor_id,
    )

    # Found Hamlet (Tier 1)
    found_res = client.post(
        f"/api/v1/campaigns/{campaign_id}/settlements",
        json={
            "name": "Pine Crossing",
            "scale": "hamlet",
            "biome": "forest_edge",
            "prosperity": 50,
            "districts": ["commons", "residential"],
        },
        headers={"x-user-id": mayor_id},
    )
    assert found_res.status_code == 201
    sid = found_res.json()["settlement_id"]

    # Attempt upgrade to Tier 2 with insufficient prosperity (50 < 100) -> 400
    fail_res = client.post(
        f"/api/v1/settlements/{sid}/upgrade-tier",
        json={"new_tier": 2, "prosperity": 50},
        headers={"x-user-id": mayor_id},
    )
    assert fail_res.status_code == 400
    assert "Insufficient civic prosperity" in fail_res.json()["detail"]

    # Upgrade with sufficient prosperity (150 >= 100) -> succeeds
    upg_res = client.post(
        f"/api/v1/settlements/{sid}/upgrade-tier",
        json={"new_tier": 2, "prosperity": 150},
        headers={"x-user-id": mayor_id},
    )
    assert upg_res.status_code == 200
    upg_data = upg_res.json()
    assert upg_data["tier"] == 2
    assert upg_data["scale"] == "village"
    assert upg_data["max_districts"] == 4
    assert "agricultural_commons" in upg_data["districts"]
    assert_event_emitted(mock_bus, "SettlementTierUpgraded")

    # CloudEvents check for SettlementTierUpgradedEvent
    tier_ce = SettlementTierUpgradedEvent(
        settlement_id=sid,
        old_tier=1,
        new_tier=2,
        unlocked_districts=["agricultural_commons"],
    ).to_cloudevent_dict()
    assert tier_ce["specversion"] == "1.0"
    assert "settlement_tier_upgraded" in tier_ce["type"]


@pytest.mark.asyncio
async def test_blackbox_establishment_upgrade_and_invariants(
    client: TestClient, spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
) -> None:
    """Verify establishment tier upgrades, amenity additions, and district boundary checks."""
    campaign_id = str(uuid4())
    user_id = f"innkeeper_{uuid4().hex[:8]}"

    await spicedb.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="player",
        subject_type="user",
        subject_id=user_id,
    )

    found_res = client.post(
        f"/api/v1/campaigns/{campaign_id}/settlements",
        json={
            "name": "Riverbend",
            "scale": "village",
            "districts": ["commons", "trading_post"],
        },
        headers={"x-user-id": user_id},
    )
    sid = found_res.json()["settlement_id"]

    # Attempt to construct in an unzoned/locked district -> 400
    invalid_dist_res = client.post(
        f"/api/v1/settlements/{sid}/establishments",
        json={
            "district_id": "nonexistent_citadel",
            "category": "hospitality",
            "name": "The Phantom Tavern",
        },
        headers={"x-user-id": user_id},
    )
    assert invalid_dist_res.status_code == 400
    assert "not zoned or unlocked" in invalid_dist_res.json()["detail"]

    # Construct valid tavern in trading_post
    tavern_res = client.post(
        f"/api/v1/settlements/{sid}/establishments",
        json={
            "district_id": "trading_post",
            "category": "hospitality",
            "name": "The Drunken Dragon Inn",
            "capacity": 30,
            "operating_cost": 10,
            "amenities": ["ale_cellar", "warm_hearth"],
        },
        headers={"x-user-id": user_id},
    )
    assert tavern_res.status_code == 201
    eid = tavern_res.json()["establishment_id"]

    # Upgrade tavern to Tier 2
    upg_res = client.post(
        f"/api/v1/establishments/{eid}/upgrade",
        json={
            "tier": 2,
            "added_amenities": ["billiards_table", "private_suites"],
            "capacity": 50,
            "operating_cost": 15,
        },
        headers={"x-user-id": user_id},
    )
    assert upg_res.status_code == 200
    upg_data = upg_res.json()
    assert upg_data["tier"] == 2
    assert upg_data["capacity"] == 50
    assert "billiards_table" in upg_data["amenities"]
    assert "private_suites" in upg_data["amenities"]
    assert "warm_hearth" in upg_data["amenities"]
    assert_event_emitted(mock_bus, "EstablishmentUpgraded")

    # CloudEvents check for EstablishmentUpgradedEvent
    upg_ce = EstablishmentUpgradedEvent(
        establishment_id=eid,
        settlement_id=sid,
        tier=2,
        added_amenities=["billiards_table"],
    ).to_cloudevent_dict()
    assert upg_ce["specversion"] == "1.0"
    assert "establishment_upgraded" in upg_ce["type"]


@pytest.mark.asyncio
async def test_blackbox_spicedb_authorization_enforcement(
    client: TestClient, spicedb: MockSpiceDBClient
) -> None:
    """Verify Zanzibar authorization denies unauthorized construction and queries."""
    campaign_id = str(uuid4())
    authorized_dm = f"dm_{uuid4().hex[:8]}"
    intruder_id = f"intruder_{uuid4().hex[:8]}"

    await spicedb.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="dungeon_master",
        subject_type="user",
        subject_id=authorized_dm,
    )

    # Intruder tries to found settlement -> 403 Forbidden
    denied_res = client.post(
        f"/api/v1/campaigns/{campaign_id}/settlements",
        json={"name": "Forbidden Outpost", "scale": "hamlet"},
        headers={"x-user-id": intruder_id},
    )
    assert denied_res.status_code == 403
    assert "Permission denied" in denied_res.json()["detail"]

    # Authorized DM founds settlement
    allowed_res = client.post(
        f"/api/v1/campaigns/{campaign_id}/settlements",
        json={"name": "Lawful Citadel", "scale": "village"},
        headers={"x-user-id": authorized_dm},
    )
    assert allowed_res.status_code == 201
    sid = allowed_res.json()["settlement_id"]

    # Intruder tries to build establishment in Lawful Citadel -> 403 Forbidden
    denied_build = client.post(
        f"/api/v1/settlements/{sid}/establishments",
        json={
            "district_id": "commons",
            "category": "underworld",
            "name": "Smuggler's Den",
        },
        headers={"x-user-id": intruder_id},
    )
    assert denied_build.status_code == 403

    # Intruder tries to view settlement without campaign/settlement permission -> 403 Forbidden
    denied_view = client.get(
        f"/api/v1/campaigns/{campaign_id}/settlements/{sid}",
        headers={"x-user-id": intruder_id},
    )
    assert denied_view.status_code == 403
