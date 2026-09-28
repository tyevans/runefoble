"""Blackbox frontdoor tests for Assignable NPC Worker Engine and Social Relationship Graph.

Governed by ADR-0001, ADR-0002, ADR-0007, ADR-0011, and Hard Invariant 7 (Blackbox TDD).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session.dependencies import set_event_bus, set_spicedb_client
from game_session.main import app
from runefoble_auth.spicedb import MockSpiceDBClient
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
async def test_blackbox_assign_worker_and_establishment_roster(
    client: TestClient, spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
) -> None:
    """Assign an armorer NPC worker to an establishment and verify roster and operations."""
    campaign_id = str(uuid4())
    dm_user_id = f"dm_{uuid4().hex[:8]}"

    await spicedb.write_relationship("campaign", campaign_id, "dungeon_master", "user", dm_user_id)
    await spicedb.write_relationship("campaign", campaign_id, "player", "user", dm_user_id)

    # 1. Found settlement via HTTP POST
    found_res = client.post(
        f"/api/v1/campaigns/{campaign_id}/settlements",
        json={
            "name": "Ironhaven",
            "scale": "market_town",
            "biome": "mountain_pass",
            "districts": ["artisan_quarter", "market_plaza"],
        },
        headers={"x-user-id": dm_user_id},
    )
    assert found_res.status_code == 201, found_res.text
    settlement_id = found_res.json()["settlement_id"]

    # 2. Construct weapon smithy establishment
    est_res = client.post(
        f"/api/v1/settlements/{settlement_id}/establishments",
        json={
            "district_id": "artisan_quarter",
            "category": "commerce",
            "name": "The Ember Anvil",
            "tier": 2,
            "operating_cost": 15,
        },
        headers={"x-user-id": dm_user_id},
    )
    assert est_res.status_code == 201, est_res.text
    establishment_id = est_res.json()["establishment_id"]

    # 3. Assign NPC armorer worker via frontdoor API
    worker_payload = {
        "name": "Torvin Ironbreaker",
        "role": "armorer",
        "wage_gold": 8,
        "mood": "content",
        "temperament": "Gruff but Honorable",
        "patience": 6,
        "traits": {
            "openness": 0.6,
            "conscientiousness": 0.85,
            "extraversion": 0.4,
            "agreeableness": 0.7,
            "neuroticism": 0.3,
        },
        "vices": ["ale", "pride"],
        "trade_proficiencies": ["blacksmithing", "armorer", "weaponsmithing"],
        "shelf_inventory": [
            {"item_id": "plate", "name": "Plate", "stock": 2, "price_gp": 150},
            {"item_id": "shield", "name": "Shield", "stock": 5, "price_gp": 20},
        ],
        "vault_inventory": [
            {"item_id": "adamantine_blade", "name": "Adamantine Blade", "stock": 1, "price_gp": 600}
        ],
        "relationships": [
            {"target_npc": "npc_baker_marta", "relation": "debtor", "intensity": 0.5}
        ],
    }

    assign_res = client.post(
        f"/api/v1/establishments/{establishment_id}/workers",
        json=worker_payload,
        headers={"x-user-id": dm_user_id},
    )
    assert assign_res.status_code == 201, assign_res.text
    worker_data = assign_res.json()
    npc_id = worker_data["npc_id"]

    assert worker_data["name"] == "Torvin Ironbreaker"
    assert worker_data["role"] == "armorer"
    assert worker_data["wage"] == 8
    assert worker_data["temperament"] == "Gruff but Honorable"
    assert len(worker_data["shelf_inventory"]) == 2
    assert len(worker_data["backroom_inventory"]) == 1
    assert len(worker_data["relationships"]) == 1

    # Verify NPCWorkerAssigned and NPCRelationshipFormed events emitted
    assert_event_emitted(mock_bus, "NPCWorkerAssigned")
    assert_event_emitted(mock_bus, "NPCRelationshipFormed")

    # 4. Assert worker shows up in establishment roster
    roster_res = client.get(
        f"/api/v1/establishments/{establishment_id}/workers",
        headers={"x-user-id": dm_user_id},
    )
    assert roster_res.status_code == 200, roster_res.text
    roster = roster_res.json()
    assert len(roster) == 1
    assert roster[0]["npc_id"] == npc_id
    assert roster[0]["name"] == "Torvin Ironbreaker"
    assert roster[0]["role"] == "armorer"

    # 5. Verify establishment operations and projected service quality updated
    est_get = client.get(
        f"/api/v1/establishments/{establishment_id}",
        headers={"x-user-id": dm_user_id},
    )
    assert est_get.status_code == 200, est_get.text
    est_data = est_get.json()
    assert est_data["staff_count"] == 1
    assert npc_id in est_data["staff"]
    assert est_data["total_wages"] == 8
    assert est_data["net_operating_cost"] == 15 + 8
    assert est_data["projected_service_quality"] >= 1.5

    # 6. Verify full roster view includes operations and social graph edges
    full_roster = client.get(
        f"/api/v1/establishments/{establishment_id}/roster",
        headers={"x-user-id": dm_user_id},
    ).json()
    assert full_roster["operations"]["total_staff"] == 1
    assert full_roster["operations"]["total_wages"] == 8
    assert len(full_roster["social_graph_edges"]) >= 1

    # Assert social relationships serialize to redstring-compatible graph edges
    edge = full_roster["social_graph_edges"][0]
    assert edge["source_id"] == npc_id
    assert edge["target_id"] == "npc_baker_marta"
    assert edge["relationship_type"] == "debtor"
    assert edge["confidence"] > 0.8
    assert "metadata" in edge

    # 7. Form secondary relationship and query worker profile directly
    rel_res = client.post(
        f"/api/v1/npcs/{npc_id}/relationships",
        json={"target_npc": "npc_apprentice_leo", "relation": "mentor", "intensity": 0.9},
        headers={"x-user-id": dm_user_id},
    )
    assert rel_res.status_code == 201
    assert len(rel_res.json()["relationships"]) == 2

    worker_get = client.get(f"/api/v1/npcs/{npc_id}", headers={"x-user-id": dm_user_id})
    assert worker_get.status_code == 200
    assert worker_get.json()["name"] == "Torvin Ironbreaker"


@pytest.mark.asyncio
async def test_blackbox_npc_mood_update_and_temperament_projection(
    client: TestClient, spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
) -> None:
    """Update NPC worker mood and assert temperament projection and service quality reflect change."""
    campaign_id = str(uuid4())
    dm_user_id = f"dm_{uuid4().hex[:8]}"

    await spicedb.write_relationship("campaign", campaign_id, "dungeon_master", "user", dm_user_id)
    await spicedb.write_relationship("campaign", campaign_id, "player", "user", dm_user_id)

    # Found settlement and bakery establishment
    client.post(
        f"/api/v1/campaigns/{campaign_id}/settlements",
        json={
            "name": "Riverdale",
            "scale": "village",
            "biome": "river_confluence",
            "districts": ["commons", "agricultural_commons"],
        },
        headers={"x-user-id": dm_user_id},
    )
    s_list = client.get(
        f"/api/v1/campaigns/{campaign_id}/settlements", headers={"x-user-id": dm_user_id}
    ).json()
    settlement_id = s_list[0]["settlement_id"]

    est_res = client.post(
        f"/api/v1/settlements/{settlement_id}/establishments",
        json={
            "district_id": "commons",
            "category": "hospitality",
            "name": "Warm Hearth Bakery",
            "tier": 1,
            "operating_cost": 5,
        },
        headers={"x-user-id": dm_user_id},
    )
    assert est_res.status_code == 201, est_res.text
    establishment_id = est_res.json()["establishment_id"]

    # Assign head baker with cheerful mood
    worker_res = client.post(
        f"/api/v1/establishments/{establishment_id}/workers",
        json={
            "name": "Marta Warmflour",
            "role": "head baker",
            "wage": 5,
            "mood": "cheerful",
            "temperament": "Warm and Welcoming",
            "patience": 8,
            "trade_proficiencies": ["baking", "pastry"],
            "shelf_inventory": [
                {
                    "item_id": "crusty_bread",
                    "name": "Crusty Hearth Loaf",
                    "stock": 20,
                    "price_gp": 1,
                }
            ],
        },
        headers={"x-user-id": dm_user_id},
    )
    worker_data = worker_res.json()
    npc_id = worker_data["npc_id"]

    # Check baseline service quality
    initial_est = client.get(
        f"/api/v1/establishments/{establishment_id}", headers={"x-user-id": dm_user_id}
    ).json()
    initial_quality = initial_est["projected_service_quality"]
    assert initial_quality >= 1.5

    # Trigger supply disruption: Update baker's mood to anxious & desperate
    mood_patch_res = client.patch(
        f"/api/v1/npcs/{npc_id}/mood",
        json={
            "mood": "desperate",
            "temperament": "Anxious and Desperate",
            "patience_delta": -4,
            "metadata": {"crisis_trigger": "river_bandits_flour_shortage"},
        },
        headers={"x-user-id": dm_user_id},
    )
    assert mood_patch_res.status_code == 200, mood_patch_res.text
    updated_worker = mood_patch_res.json()

    assert updated_worker["mood"] == "desperate"
    assert updated_worker["temperament"] == "Anxious and Desperate"
    assert updated_worker["patience"] == 4
    assert updated_worker["metadata"]["crisis_trigger"] == "river_bandits_flour_shortage"

    # Verify NPCMoodUpdated domain event emitted
    assert_event_emitted(mock_bus, "NPCMoodUpdated")

    # Assert establishment projected service quality reflects the negative mood shift
    updated_est = client.get(
        f"/api/v1/establishments/{establishment_id}", headers={"x-user-id": dm_user_id}
    ).json()
    assert updated_est["projected_service_quality"] < initial_quality


@pytest.mark.asyncio
async def test_blackbox_worker_authorization_and_relieving(
    client: TestClient, spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
) -> None:
    """Verify SpiceDB Zanzibar permissions enforce hiring/managing and worker relieving."""
    campaign_id = str(uuid4())
    owner_id = f"owner_{uuid4().hex[:8]}"
    unauthorized_id = f"intruder_{uuid4().hex[:8]}"

    await spicedb.write_relationship("campaign", campaign_id, "dungeon_master", "user", owner_id)
    await spicedb.write_relationship("campaign", campaign_id, "player", "user", owner_id)

    # Found settlement and tavern establishment
    found = client.post(
        f"/api/v1/campaigns/{campaign_id}/settlements",
        json={
            "name": "Oasis Haven",
            "scale": "village",
            "biome": "desert_oasis",
            "districts": ["commons", "trading_post"],
        },
        headers={"x-user-id": owner_id},
    ).json()
    settlement_id = found["settlement_id"]

    est_res = client.post(
        f"/api/v1/settlements/{settlement_id}/establishments",
        json={"district_id": "commons", "category": "hospitality", "name": "The Dune Flagon"},
        headers={"x-user-id": owner_id},
    )
    assert est_res.status_code == 201, est_res.text
    establishment_id = est_res.json()["establishment_id"]

    # Unauthorized user cannot assign worker
    unauth_assign = client.post(
        f"/api/v1/establishments/{establishment_id}/workers",
        json={"name": "Boris Bouncer", "role": "bouncer"},
        headers={"x-user-id": unauthorized_id},
    )
    assert unauth_assign.status_code == 403

    # Authorized user assigns bouncer
    auth_assign = client.post(
        f"/api/v1/establishments/{establishment_id}/workers",
        json={
            "name": "Boris Bouncer",
            "role": "bouncer",
            "wage": 4,
            "trade_proficiencies": ["security"],
        },
        headers={"x-user-id": owner_id},
    )
    assert auth_assign.status_code == 201
    npc_id = auth_assign.json()["npc_id"]

    # Unauthorized user cannot modify mood
    unauth_mood = client.patch(
        f"/api/v1/npcs/{npc_id}/mood",
        json={"mood": "furious", "temperament": "Violent"},
        headers={"x-user-id": unauthorized_id},
    )
    assert unauth_mood.status_code == 403

    # Relieve worker from duty
    relieve_res = client.post(
        f"/api/v1/establishments/{establishment_id}/workers/{npc_id}/relieve",
        json={"reason": "Caught drinking on shift"},
        headers={"x-user-id": owner_id},
    )
    assert relieve_res.status_code == 200, relieve_res.text
    assert relieve_res.json()["status"] == "relieved"
    assert_event_emitted(mock_bus, "NPCWorkerRelieved")

    # Verify roster is now empty of active workers
    roster_res = client.get(
        f"/api/v1/establishments/{establishment_id}/workers",
        headers={"x-user-id": owner_id},
    )
    assert roster_res.status_code == 200
    assert len(roster_res.json()) == 0
