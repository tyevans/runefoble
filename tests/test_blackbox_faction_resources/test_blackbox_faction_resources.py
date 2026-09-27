"""Blackbox TDD test suite for NPC Faction Resources and Bribery Mechanics (TASK-0161).

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0006: Redis Streams Distributed Domain Event Streaming
- ADR-0007: Domain-Driven Design Architecture
- ADR-0011: PostgreSQL Event Store via eventsource-py
- Hard Invariant 1: Object-level Zanzibar authorization via SpiceDB
- Hard Invariant 2: Domain state changes flow strictly through DeclarativeAggregate subclasses
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from eventsource.domain.event_registry import get_event_class_or_none
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient
from runefoble_events import (
    FactionBriberyAttempted,
    FactionBriberyAttemptedEvent,
    FactionMercenaryRecruited,
    FactionMercenaryRecruitedEvent,
    FactionResourceUpdated,
    FactionResourceUpdatedEvent,
)
from runefoble_platform.event_sourcing import (
    AggregateRepository,
    InMemoryEventBus,
    InMemoryEventStore,
)
from runefoble_platform.redis_bus import MockAsyncRedis, RedisStreamsEventBus
from the_watcher.dependencies import (
    get_spicedb_client,
    set_event_bus,
    set_faction_resource_repo,
    set_spicedb_client,
)
from the_watcher.factions.resources.aggregate import FactionResourceAggregate
from the_watcher.main import app


@pytest.fixture(autouse=True)
def clean_resource_environment():
    """Configure mock SpiceDB, event store, bus, and repo before each test."""
    set_spicedb_client(MockSpiceDBClient())
    set_event_bus(RedisStreamsEventBus(client=MockAsyncRedis()))
    test_store = InMemoryEventStore()
    test_bus = InMemoryEventBus()
    repo = AggregateRepository(
        event_store=test_store,
        aggregate_factory=FactionResourceAggregate,
        event_publisher=test_bus,
    )
    set_faction_resource_repo(repo)
    yield
    set_spicedb_client(SpiceDBClient())
    set_event_bus(None)
    set_faction_resource_repo(None)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


async def _setup_campaign_roles(
    dm_user: str = "dm_evelyn", player_user: str = "player_valeros"
) -> tuple[str, str, str]:
    """Helper to seed SpiceDB Zanzibar roles on a campaign."""
    camp_id = str(uuid4())
    spicedb = get_spicedb_client()
    await spicedb.write_relationship(
        resource_type="campaign",
        resource_id=camp_id,
        relation="dungeon_master",
        subject_type="user",
        subject_id=dm_user,
    )
    await spicedb.write_relationship(
        resource_type="campaign",
        resource_id=camp_id,
        relation="player",
        subject_type="user",
        subject_id=player_user,
    )
    return camp_id, dm_user, player_user


def test_cloudevents_registration():
    """Verify faction resource domain events are registered and conform to CloudEvents."""
    events = [
        ("runefoble.events.watcher.faction_resource_updated", FactionResourceUpdatedEvent),
        ("runefoble.events.watcher.faction_mercenary_recruited", FactionMercenaryRecruitedEvent),
        ("runefoble.events.watcher.faction_bribery_attempted", FactionBriberyAttemptedEvent),
    ]
    for type_name, expected_cls in events:
        assert get_event_class_or_none(type_name) == expected_cls

    assert FactionResourceUpdated == FactionResourceUpdatedEvent
    assert FactionMercenaryRecruited == FactionMercenaryRecruitedEvent
    assert FactionBriberyAttempted == FactionBriberyAttemptedEvent

    sample_event = FactionResourceUpdatedEvent(
        faction_id="faction-ironfang",
        campaign_id="camp-100",
        treasury=500,
        contraband=20,
        mercenaries_count=10,
        delta_treasury=150,
        delta_contraband=5,
        reason="smuggling_booty",
    )
    ce = sample_event.to_cloudevent_dict()
    assert ce["specversion"] == "1.0"
    assert ce["type"] == "runefoble.events.watcher.faction_resource_updated"
    assert ce["data"]["faction_id"] == "faction-ironfang"
    assert ce["data"]["treasury"] == 500


@pytest.mark.asyncio
async def test_zanzibar_faction_resource_authorization(client: TestClient):
    """Verify unauthorized users cannot adjust resources or bribery, while DMs can."""
    camp_id, dm_user, player_user = await _setup_campaign_roles()
    faction_id = f"fact-{uuid4().hex[:8]}"

    # Unauthorized player attempts resource adjustment -> 403 Forbidden
    res_player_adj = client.post(
        f"/factions/{faction_id}/resources/adjust",
        json={"treasury_delta": 100, "campaign_id": camp_id},
        headers={"X-User-Id": player_user},
    )
    assert res_player_adj.status_code == 403
    assert "Forbidden" in res_player_adj.json()["detail"]

    # Unauthorized player attempts bribery -> 403 Forbidden
    res_player_bribe = client.post(
        f"/factions/{faction_id}/bribery/resolve",
        json={"target_name": "Guard Captain", "bribe_amount": 50, "campaign_id": camp_id},
        headers={"X-User-Id": player_user},
    )
    assert res_player_bribe.status_code == 403

    # Unauthorized player attempts mercenary recruitment -> 403 Forbidden
    res_player_recruit = client.post(
        f"/factions/{faction_id}/mercenaries/recruit",
        json={"unit_name": "Archers", "count": 2, "cost_per_unit": 10, "campaign_id": camp_id},
        headers={"X-User-Id": player_user},
    )
    assert res_player_recruit.status_code == 403

    # Player CAN view resources (Zanzibar campaign->view permission)
    res_view_player = client.get(
        f"/factions/{faction_id}/resources?campaign_id={camp_id}",
        headers={"X-User-Id": player_user},
    )
    assert res_view_player.status_code == 200

    # DM execution succeeds
    res_dm = client.post(
        f"/factions/{faction_id}/resources/adjust",
        json={"treasury_delta": 200, "campaign_id": camp_id},
        headers={"X-User-Id": dm_user},
    )
    assert res_dm.status_code == 200
    assert res_dm.json()["treasury"] == 300  # Default 100 + 200


@pytest.mark.asyncio
async def test_frontdoor_resource_adjust_and_query(client: TestClient):
    """Verify frontdoor API adjusts treasury, contraband, and persists aggregate state."""
    camp_id, dm_user, _ = await _setup_campaign_roles()
    faction_id = f"fact-{uuid4().hex[:8]}"

    # Add 250 treasury and 15 contraband
    res = client.post(
        f"/factions/{faction_id}/resources/adjust",
        json={
            "treasury_delta": 250,
            "contraband_delta": 15,
            "reason": "dock_heist",
            "campaign_id": camp_id,
        },
        headers={"X-User-Id": dm_user},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["treasury"] == 350
    assert data["contraband_score"] == 15

    # Query via GET
    get_res = client.get(
        f"/factions/{faction_id}/resources?campaign_id={camp_id}",
        headers={"X-User-Id": dm_user},
    )
    assert get_res.status_code == 200
    assert get_res.json()["treasury"] == 350
    assert get_res.json()["contraband_score"] == 15

    # Spend 50 gold
    spend_res = client.post(
        f"/factions/{faction_id}/resources/adjust",
        json={"treasury_delta": -50, "reason": "informant_fee", "campaign_id": camp_id},
        headers={"X-User-Id": dm_user},
    )
    assert spend_res.status_code == 200
    assert spend_res.json()["treasury"] == 300


@pytest.mark.asyncio
async def test_frontdoor_mercenary_recruiting_and_upkeep(client: TestClient):
    """Verify hiring mercenaries updates troop counts, calculates upkeep, and rejects deficits."""
    camp_id, dm_user, _ = await _setup_campaign_roles()
    faction_id = f"fact-{uuid4().hex[:8]}"

    # Set treasury to 200
    client.post(
        f"/factions/{faction_id}/resources/adjust",
        json={"treasury_delta": 100, "campaign_id": camp_id},
        headers={"X-User-Id": dm_user},
    )

    # Recruit 4 veterans at 25 gold each (100 total, upkeep 2 each)
    rec_res = client.post(
        f"/factions/{faction_id}/mercenaries/recruit",
        json={
            "unit_name": "Black Skull Enforcers",
            "count": 4,
            "cost_per_unit": 25,
            "unit_type": "heavy_infantry",
            "upkeep_per_tick": 2,
            "campaign_id": camp_id,
        },
        headers={"X-User-Id": dm_user},
    )
    assert rec_res.status_code == 200
    data = rec_res.json()
    assert data["treasury"] == 100  # 200 - 100
    assert data["mercenaries_count"] == 4
    assert data["upkeep_cost"] == 8  # 4 * 2

    # Attempt to recruit beyond treasury (needs 150, only has 100) -> 400 Bad Request
    fail_res = client.post(
        f"/factions/{faction_id}/mercenaries/recruit",
        json={
            "unit_name": "Siege Engineers",
            "count": 3,
            "cost_per_unit": 50,
            "campaign_id": camp_id,
        },
        headers={"X-User-Id": dm_user},
    )
    assert fail_res.status_code == 400
    assert "Insufficient treasury" in fail_res.json()["detail"]


@pytest.mark.asyncio
async def test_frontdoor_bribery_resolution_mechanics(client: TestClient):
    """Verify bribery difficulty thresholds against target loyalty and counter-bribes."""
    camp_id, dm_user, _ = await _setup_campaign_roles()
    faction_id = f"fact-{uuid4().hex[:8]}"

    # Add ample treasury
    client.post(
        f"/factions/{faction_id}/resources/adjust",
        json={"treasury_delta": 400, "campaign_id": camp_id},
        headers={"X-User-Id": dm_user},
    )

    # 1. Bribe corruptible dock official with 100 gold
    # Base DC 15 - 3 (corruptible) + 2 (official) = 14. Bribe 100 gives modifier +2. Roll 12 -> total 14 >= 14 (Success)
    bribe_res = client.post(
        f"/factions/{faction_id}/bribery/resolve",
        json={
            "target_name": "Clerk Garrow",
            "target_role": "official",
            "bribe_amount": 100,
            "target_loyalty": "corruptible",
            "counter_bribe": 0,
            "roll": 12,
            "campaign_id": camp_id,
        },
        headers={"X-User-Id": dm_user},
    )
    assert bribe_res.status_code == 200
    b_data = bribe_res.json()
    assert b_data["success"] is True
    assert b_data["outcome"] == "success"
    assert b_data["remaining_treasury"] == 400  # 500 - 100

    # 2. Bribe loyal guard captain countered by rival's 150 gold counter-bribe
    # Base DC 15 + 5 (loyal) + 3 (guard_captain) + 3 (counter_bribe//50) = 26. Roll 10 + modifier 1 = 11 < 26 (Countered)
    counter_res = client.post(
        f"/factions/{faction_id}/bribery/resolve",
        json={
            "target_name": "Captain Vane",
            "target_role": "guard_captain",
            "bribe_amount": 50,
            "target_loyalty": "loyal",
            "counter_bribe": 150,
            "roll": 10,
            "campaign_id": camp_id,
        },
        headers={"X-User-Id": dm_user},
    )
    assert counter_res.status_code == 200
    c_data = counter_res.json()
    assert c_data["success"] is False
    assert c_data["outcome"] == "countered"
    assert "rival's 150 gold counter-bribe" in c_data["narrative"]

    # 3. Critical success on natural 20
    crit_res = client.post(
        f"/factions/{faction_id}/bribery/resolve",
        json={
            "target_name": "High Magistrate",
            "target_role": "judge",
            "bribe_amount": 50,
            "target_loyalty": "incorruptible",
            "counter_bribe": 0,
            "roll": 20,
            "campaign_id": camp_id,
        },
        headers={"X-User-Id": dm_user},
    )
    assert crit_res.status_code == 200
    assert crit_res.json()["outcome"] == "critical_success"

    # 4. Critical failure on natural 1
    fail_res = client.post(
        f"/factions/{faction_id}/bribery/resolve",
        json={
            "target_name": "City Watchman",
            "target_role": "guard",
            "bribe_amount": 50,
            "target_loyalty": "neutral",
            "counter_bribe": 0,
            "roll": 1,
            "campaign_id": camp_id,
        },
        headers={"X-User-Id": dm_user},
    )
    assert fail_res.status_code == 200
    assert fail_res.json()["outcome"] == "critical_failure"
    assert "raised an alarm" in fail_res.json()["narrative"]

    # 5. Insufficient treasury check
    broke_res = client.post(
        f"/factions/{faction_id}/bribery/resolve",
        json={
            "target_name": "Guildmaster",
            "bribe_amount": 5000,
            "campaign_id": camp_id,
        },
        headers={"X-User-Id": dm_user},
    )
    assert broke_res.status_code == 400
    assert "Insufficient treasury" in broke_res.json()["detail"]
