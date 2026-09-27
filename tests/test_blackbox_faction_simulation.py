"""Blackbox TDD test suite for Autonomous NPC Faction Agendas & Background Simulation Engine (TASK-0126).

Governed by:
- ADR-0002: Event-Driven Watcher Gameplay Orchestration
- ADR-0006: Redis Streams Event Bus
- ADR-0011: eventsource-py Core Event Sourcing
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
    FactionAgendaAdvanced,
    FactionAgendaSet,
    FactionCreated,
    GeopoliticalShiftOccurred,
    WorldTickExecuted,
)
from runefoble_platform.event_sourcing import (
    AggregateRepository,
    InMemoryEventBus,
    InMemoryEventStore,
)
from runefoble_platform.redis_bus import MockAsyncRedis, RedisStreamsEventBus
from the_watcher.dependencies import (
    get_faction_simulation_engine,
    get_spicedb_client,
    set_event_bus,
    set_faction_repo,
    set_spicedb_client,
)
from the_watcher.factions import FactionAggregate
from the_watcher.main import app


@pytest.fixture(autouse=True)
def clean_simulation_environment():
    """Ensure clean SpiceDB, simulation engine, event store, and bus before and after each test."""
    set_spicedb_client(MockSpiceDBClient())
    set_event_bus(RedisStreamsEventBus(client=MockAsyncRedis()))
    test_store = InMemoryEventStore()
    test_bus = InMemoryEventBus()
    repo = AggregateRepository(
        event_store=test_store,
        aggregate_factory=FactionAggregate,
        event_publisher=test_bus,
    )
    set_faction_repo(repo)
    engine = get_faction_simulation_engine()
    engine.clear()
    yield
    engine.clear()
    set_spicedb_client(SpiceDBClient())
    set_event_bus(None)
    set_faction_repo(None)


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


def test_faction_cloudevents_registration():
    """Verify faction domain events are properly registered in EventRegistry and serializable."""
    events = [
        ("runefoble.events.watcher.faction_created", FactionCreated),
        ("runefoble.events.watcher.faction_agenda_set", FactionAgendaSet),
        ("runefoble.events.watcher.faction_agenda_advanced", FactionAgendaAdvanced),
        ("runefoble.events.watcher.geopolitical_shift_occurred", GeopoliticalShiftOccurred),
        ("runefoble.events.watcher.world_tick_executed", WorldTickExecuted),
    ]
    for type_name, expected_cls in events:
        assert get_event_class_or_none(type_name) == expected_cls

    shift = GeopoliticalShiftOccurred(
        campaign_id="camp-100",
        faction_id="fact-1",
        territory="Oakhaven Docks",
        shift_type="trade_shortage",
        description="Illicit weapons flooded the docks.",
        severity="critical",
        ripple_effects=["Merchant weapons markup increased by 25%"],
    )
    ce = shift.to_cloudevent_dict()
    assert ce["specversion"] == "1.0"
    assert ce["type"] == "runefoble.events.watcher.geopolitical_shift_occurred"
    assert ce["data"]["faction_id"] == "fact-1"
    assert ce["data"]["shift_type"] == "trade_shortage"


@pytest.mark.asyncio
async def test_zanzibar_world_tick_authorization(client: TestClient):
    """Verify unauthorized players cannot advance world ticks, while DMs can."""
    camp_id, dm_user, player_user = await _setup_campaign_roles()

    # Player attempt to trigger world-tick -> 403 Forbidden
    res_player = client.post(
        f"/api/v1/campaigns/{camp_id}/world-tick",
        json={"regional_stability": 50},
        headers={"X-User-Id": player_user},
    )
    assert res_player.status_code == 403
    assert "Forbidden" in res_player.json()["detail"]

    # Player attempt to register faction -> 403 Forbidden
    res_create_player = client.post(
        f"/api/v1/campaigns/{camp_id}/factions",
        json={"name": "Rogue Band", "influence": 30},
        headers={"X-User-Id": player_user},
    )
    assert res_create_player.status_code == 403

    # Player CAN view factions (Zanzibar campaign->view permission)
    res_view_player = client.get(
        f"/api/v1/campaigns/{camp_id}/factions",
        headers={"X-User-Id": player_user},
    )
    assert res_view_player.status_code == 200

    # DM execution succeeds
    res_dm = client.post(
        f"/api/v1/campaigns/{camp_id}/world-tick",
        json={"regional_stability": 50},
        headers={"X-User-Id": dm_user},
    )
    assert res_dm.status_code == 200
    assert res_dm.json()["tick_number"] == 1


@pytest.mark.asyncio
async def test_frontdoor_faction_creation_and_query(client: TestClient):
    """Verify registering a custom faction via frontdoor API persists aggregate and enables query."""
    camp_id, dm_user, _ = await _setup_campaign_roles()

    payload = {
        "name": "Ironfang Syndicate",
        "influence": 65,
        "resources": 50,
        "disposition": "hostile",
        "active_goal": "Smuggle Arcane Weapons into Oakhaven",
        "territory": "Oakhaven Docks",
        "rival_faction_ids": [],
    }
    create_res = client.post(
        f"/api/v1/campaigns/{camp_id}/factions",
        json=payload,
        headers={"X-User-Id": dm_user},
    )
    assert create_res.status_code == 200
    faction_data = create_res.json()
    assert faction_data["name"] == "Ironfang Syndicate"
    assert faction_data["active_goal"] == "Smuggle Arcane Weapons into Oakhaven"
    assert faction_data["influence"] == 65
    faction_id = faction_data["faction_id"]

    # Get single faction frontdoor
    get_res = client.get(
        f"/api/v1/campaigns/{camp_id}/factions/{faction_id}",
        headers={"X-User-Id": dm_user},
    )
    assert get_res.status_code == 200
    assert get_res.json()["faction_id"] == faction_id
    assert get_res.json()["territory"] == "Oakhaven Docks"

    # List factions frontdoor
    list_res = client.get(
        f"/api/v1/campaigns/{camp_id}/factions",
        headers={"X-User-Id": dm_user},
    )
    assert list_res.status_code == 200
    assert any(f["faction_id"] == faction_id for f in list_res.json())


@pytest.mark.asyncio
async def test_downtime_world_tick_advances_agendas_and_rumors(client: TestClient):
    """Verify executing a world tick advances faction agendas and generates intelligence bulletin."""
    camp_id, dm_user, _ = await _setup_campaign_roles()

    # Execute simulation tick via /api/v1/campaigns/{id}/world-tick
    tick_payload = {
        "regional_stability": 60,
        "random_seed": 42,
        "custom_rumors": ["Strange purple flares seen above Oakhaven lighthouse."],
    }
    res = client.post(
        f"/api/v1/campaigns/{camp_id}/world-tick",
        json=tick_payload,
        headers={"X-User-Id": dm_user},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["campaign_id"] == camp_id
    assert data["tick_number"] == 1
    assert len(data["factions"]) >= 3
    assert len(data["tavern_rumors"]) >= 1
    assert "Strange purple flares seen above Oakhaven lighthouse." in data["tavern_rumors"]

    # Verify bulletin format
    bulletin = data["intelligence_bulletin"]
    assert "THE WATCHER INTELLIGENCE BULLETIN: WORLD TICK #1" in bulletin
    assert "Geopolitical & Territorial Shifts" in bulletin
    assert "Faction Agenda Progress" in bulletin
    assert "Evolving Tavern Rumors" in bulletin

    # Also verify alias endpoint POST /api/v1/campaigns/{id}/factions/tick
    alias_res = client.post(
        f"/api/v1/campaigns/{camp_id}/factions/tick",
        json={"regional_stability": 50, "random_seed": 77},
        headers={"X-User-Id": dm_user},
    )
    assert alias_res.status_code == 200
    assert alias_res.json()["tick_number"] == 2


@pytest.mark.asyncio
async def test_agenda_completion_triggers_geopolitical_shift(client: TestClient):
    """Verify that when a faction completes an agenda, a geopolitical shift occurs with ripple effects."""
    camp_id, dm_user, _ = await _setup_campaign_roles()

    # Create a faction nearly done with their agenda
    payload = {
        "name": "Ironfang Syndicate",
        "influence": 80,
        "resources": 70,
        "disposition": "hostile",
        "active_goal": "Smuggle Arcane Weapons into Oakhaven",
        "territory": "Oakhaven Docks",
    }
    create_res = client.post(
        f"/api/v1/campaigns/{camp_id}/factions",
        json=payload,
        headers={"X-User-Id": dm_user},
    )
    faction_id = create_res.json()["faction_id"]
    assert faction_id.startswith("faction-")

    # Perform multiple ticks with high stability to guarantee progress completion
    shift_detected = False
    for seed in [1, 2, 3, 4]:
        res = client.post(
            f"/api/v1/campaigns/{camp_id}/world-tick",
            json={"regional_stability": 50, "random_seed": seed},
            headers={"X-User-Id": dm_user},
        )
        assert res.status_code == 200
        shifts = res.json()["shifts"]
        if any(s["faction_name"] == "Ironfang Syndicate" for s in shifts):
            shift_detected = True
            shift = next(s for s in shifts if s["faction_name"] == "Ironfang Syndicate")
            assert shift["shift_type"] == "trade_shortage"
            assert "Oakhaven Docks" in shift["territory"]
            assert len(shift["ripple_effects"]) > 0
            break

    assert shift_detected, "Geopolitical shift should have triggered upon agenda completion"

    # Verify latest bulletin query
    latest_res = client.get(
        f"/api/v1/campaigns/{camp_id}/world-ticks/latest",
        headers={"X-User-Id": dm_user},
    )
    assert latest_res.status_code == 200
    assert latest_res.json()["tick_number"] >= 1
