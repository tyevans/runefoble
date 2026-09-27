"""Blackbox TDD test suite for Faction Turf War and Regional Unrest Pipeline (TASK-0162).

Governed by:
- ADR-0002: Event-Driven Watcher Gameplay Orchestration
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0006: Redis Streams Distributed Domain Event Streaming
- ADR-0007: Domain-Driven Design Architecture
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
    FactionSkirmishResolved,
    FactionSkirmishResolvedEvent,
    FactionTerritoryCaptured,
    FactionTerritoryCapturedEvent,
    RegionalUnrestEscalated,
    RegionalUnrestEscalatedEvent,
)
from runefoble_platform.event_sourcing import (
    AggregateRepository,
    InMemoryEventBus,
    InMemoryEventStore,
)
from runefoble_platform.redis_bus import MockAsyncRedis, RedisStreamsEventBus
from the_watcher.dependencies import (
    STREAM_WORLD,
    get_spicedb_client,
    set_event_bus,
    set_regional_unrest_repo,
    set_spicedb_client,
)
from the_watcher.main import app
from the_watcher.turf_war.aggregate import RegionalUnrestAggregate
from the_watcher.turf_war.unrest_calculator import UnrestCalculator


@pytest.fixture
def mock_redis() -> MockAsyncRedis:
    return MockAsyncRedis()


@pytest.fixture(autouse=True)
def clean_turf_war_environment(mock_redis: MockAsyncRedis):
    """Configure mock SpiceDB, event store, mock redis bus, and unrest repo before each test."""
    set_spicedb_client(MockSpiceDBClient())
    bus = RedisStreamsEventBus(client=mock_redis)
    set_event_bus(bus)

    test_store = InMemoryEventStore()
    test_bus = InMemoryEventBus()
    repo = AggregateRepository(
        event_store=test_store,
        aggregate_factory=RegionalUnrestAggregate,
        event_publisher=test_bus,
    )
    set_regional_unrest_repo(repo)

    yield

    set_spicedb_client(SpiceDBClient())
    set_event_bus(None)
    set_regional_unrest_repo(None)


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
    """Verify turf war domain events are registered and produce valid CloudEvents 1.0."""
    events = [
        ("runefoble.events.watcher.faction_skirmish_resolved", FactionSkirmishResolvedEvent),
        ("runefoble.events.watcher.faction_territory_captured", FactionTerritoryCapturedEvent),
        ("runefoble.events.watcher.regional_unrest_escalated", RegionalUnrestEscalatedEvent),
    ]
    for type_name, expected_cls in events:
        assert get_event_class_or_none(type_name) == expected_cls

    assert FactionSkirmishResolved == FactionSkirmishResolvedEvent
    assert FactionTerritoryCaptured == FactionTerritoryCapturedEvent
    assert RegionalUnrestEscalated == RegionalUnrestEscalatedEvent

    sample_event = FactionSkirmishResolvedEvent(
        skirmish_id="skm-test-1",
        campaign_id="camp-10",
        region_id="region-valen",
        contested_node="North Watchtower",
        attacker_faction_id="ironfang",
        defender_faction_id="city_guard",
        winning_faction_id="ironfang",
        attacker_casualties=2,
        defender_casualties=8,
        territory_captured=True,
        unrest_delta=17,
        narrative="Ironfang vanguard shattered the perimeter.",
    )
    ce = sample_event.to_cloudevent_dict()
    assert ce["specversion"] == "1.0"
    assert ce["type"] == "runefoble.events.watcher.faction_skirmish_resolved"
    assert ce["data"]["skirmish_id"] == "skm-test-1"
    assert ce["data"]["winning_faction_id"] == "ironfang"
    assert ce["data"]["territory_captured"] is True


@pytest.mark.asyncio
async def test_zanzibar_turf_war_authorization(client: TestClient):
    """Verify Zanzibar authorization: non-DMs cannot simulate skirmishes; DMs can."""
    camp_id, dm_user, player_user = await _setup_campaign_roles()
    region_id = f"reg-{uuid4().hex[:8]}"

    payload = {
        "campaign_id": camp_id,
        "region_id": region_id,
        "contested_node": "West River Gate",
        "attacker": {"faction_id": "ironfang", "military_strength": 30},
        "defender": {"faction_id": "guard", "military_strength": 20},
        "terrain": "plains",
    }

    # Unauthorized player -> 403 Forbidden
    res_player = client.post(
        "/the-watcher/factions/skirmish/simulate",
        json=payload,
        headers={"X-User-Id": player_user},
    )
    assert res_player.status_code == 403
    assert "Forbidden" in res_player.json()["detail"]

    # Authorized DM -> 200 OK
    res_dm = client.post(
        "/the-watcher/factions/skirmish/simulate",
        json=payload,
        headers={"X-User-Id": dm_user},
    )
    assert res_dm.status_code == 200
    data = res_dm.json()
    assert data["region_id"] == region_id
    assert data["contested_node"] == "West River Gate"


@pytest.mark.asyncio
async def test_skirmish_simulation_attacker_victory_and_territory_capture(
    client: TestClient, mock_redis: MockAsyncRedis
):
    """Verify decisive attacker victory captures territory and escalates regional unrest."""
    camp_id, dm_user, _ = await _setup_campaign_roles()
    region_id = f"reg-{uuid4().hex[:8]}"

    payload = {
        "campaign_id": camp_id,
        "region_id": region_id,
        "contested_node": "Smugglers Cove",
        "attacker": {"faction_id": "blood_corsairs", "military_strength": 50, "morale_modifier": 2},
        "defender": {"faction_id": "harbor_militia", "military_strength": 20, "defense_rating": 2},
        "terrain": "plains",
        "attacker_roll": 18,
        "defender_roll": 4,
    }

    res = client.post(
        "/the-watcher/factions/skirmish/simulate",
        json=payload,
        headers={"X-User-Id": dm_user},
    )
    assert res.status_code == 200
    data = res.json()

    assert data["winner_faction_id"] == "blood_corsairs"
    assert data["loser_faction_id"] == "harbor_militia"
    assert data["territory_captured"] is True
    assert data["controlling_faction_id"] == "blood_corsairs"
    assert data["defender_casualties"] > 5
    assert data["unrest_delta"] > 10
    assert data["current_unrest"] == data["unrest_delta"]
    assert data["alert_level"] in ["calm", "guarded", "elevated", "high", "critical"]
    assert "Smugglers Cove" in data["narrative"]

    # Verify state via GET query endpoint
    res_get = client.get(
        f"/the-watcher/regions/{region_id}/unrest?campaign_id={camp_id}",
        headers={"X-User-Id": dm_user},
    )
    assert res_get.status_code == 200
    state_data = res_get.json()
    assert state_data["controlling_faction_id"] == "blood_corsairs"
    assert state_data["unrest_score"] == data["current_unrest"]
    assert "Smugglers Cove" in state_data["contested_nodes"]
    assert len(state_data["recent_skirmishes"]) == 1

    # Verify domain events fanned out to Redis Streams STREAM_WORLD
    assert STREAM_WORLD in mock_redis.streams
    published_events = mock_redis.streams[STREAM_WORLD]
    assert len(published_events) >= 2  # Skirmish resolved, territory captured, unrest escalated


@pytest.mark.asyncio
async def test_skirmish_simulation_defender_hold_terrain_advantage(client: TestClient):
    """Verify defender with strong fortification advantage repels attackers."""
    camp_id, dm_user, _ = await _setup_campaign_roles()
    region_id = f"reg-{uuid4().hex[:8]}"

    payload = {
        "campaign_id": camp_id,
        "region_id": region_id,
        "contested_node": "High Stone Citadel",
        "attacker": {"faction_id": "goblin_horde", "military_strength": 25},
        "defender": {"faction_id": "dwarf_legion", "military_strength": 30, "defense_rating": 5},
        "terrain": "fortress",
        "attacker_roll": 5,
        "defender_roll": 16,
    }

    res = client.post(
        "/the-watcher/factions/skirmish/simulate",
        json=payload,
        headers={"X-User-Id": dm_user},
    )
    assert res.status_code == 200
    data = res.json()

    assert data["winner_faction_id"] == "dwarf_legion"
    assert data["loser_faction_id"] == "goblin_horde"
    assert data["territory_captured"] is False
    assert data["controlling_faction_id"] == "dwarf_legion"
    assert data["attacker_casualties"] > data["defender_casualties"]


@pytest.mark.asyncio
async def test_skirmish_stalemate_resolution(client: TestClient):
    """Verify equal strength and rolls result in a bloody stalemate."""
    camp_id, dm_user, _ = await _setup_campaign_roles()
    region_id = f"reg-{uuid4().hex[:8]}"

    payload = {
        "campaign_id": camp_id,
        "region_id": region_id,
        "contested_node": "Dead Man Crossroads",
        "attacker": {"faction_id": "guild_a", "military_strength": 20},
        "defender": {"faction_id": "guild_b", "military_strength": 20, "defense_rating": 0},
        "terrain": "plains",
        "attacker_roll": 10,
        "defender_roll": 10,
    }

    res = client.post(
        "/the-watcher/factions/skirmish/simulate",
        json=payload,
        headers={"X-User-Id": dm_user},
    )
    assert res.status_code == 200
    data = res.json()

    assert data["is_stalemate"] is True
    assert data["territory_captured"] is False
    assert "stalemate" in data["narrative"].lower()


@pytest.mark.asyncio
async def test_regional_unrest_progression_and_economic_friction(client: TestClient):
    """Verify progressive skirmishes push unrest into critical martial law and increase friction."""
    camp_id, dm_user, _ = await _setup_campaign_roles()
    region_id = f"reg-{uuid4().hex[:8]}"

    # Clash 1
    client.post(
        "/the-watcher/factions/skirmish/simulate",
        json={
            "campaign_id": camp_id,
            "region_id": region_id,
            "contested_node": "Outer Gate",
            "attacker": {"faction_id": "f_atk", "military_strength": 40},
            "defender": {"faction_id": "f_def", "military_strength": 30},
            "terrain": "urban",
        },
        headers={"X-User-Id": dm_user},
    )

    # Clash 2
    client.post(
        "/the-watcher/factions/skirmish/simulate",
        json={
            "campaign_id": camp_id,
            "region_id": region_id,
            "contested_node": "Market Square",
            "attacker": {"faction_id": "f_atk", "military_strength": 50},
            "defender": {"faction_id": "f_def", "military_strength": 35},
            "terrain": "urban",
        },
        headers={"X-User-Id": dm_user},
    )

    # Clash 3
    client.post(
        "/the-watcher/factions/skirmish/simulate",
        json={
            "campaign_id": camp_id,
            "region_id": region_id,
            "contested_node": "Keep Armory",
            "attacker": {"faction_id": "f_atk", "military_strength": 60},
            "defender": {"faction_id": "f_def", "military_strength": 40},
            "terrain": "fortress",
        },
        headers={"X-User-Id": dm_user},
    )

    # Query unrest projection
    res = client.get(
        f"/the-watcher/regions/{region_id}/unrest?campaign_id={camp_id}",
        headers={"X-User-Id": dm_user},
    )
    assert res.status_code == 200
    info = res.json()
    assert info["unrest_score"] >= 30
    assert len(info["contested_nodes"]) >= 2
    assert len(info["recent_skirmishes"]) == 3
    assert info["economic_friction"] > 0.2
    assert info["security_level"] in ["patrolled", "heightened", "curfew", "martial_law"]


def test_unrest_calculator_edge_cases():
    """Verify UnrestCalculator metrics, clamping, and peace stabilization decay."""
    calc = UnrestCalculator()
    assert calc.calculate_alert_level(0) == "calm"
    assert calc.calculate_alert_level(30) == "guarded"
    assert calc.calculate_alert_level(60) == "elevated"
    assert calc.calculate_alert_level(80) == "high"
    assert calc.calculate_alert_level(95) == "critical"

    assert calc.calculate_security_level("calm") == "standard"
    assert calc.calculate_security_level("high") == "curfew"
    assert calc.calculate_security_level("critical") == "martial_law"

    # Economic friction between 0.0 and 1.0
    assert calc.calculate_economic_friction(0) == 0.0
    assert calc.calculate_economic_friction(50) == 0.45
    assert calc.calculate_economic_friction(100) == 0.9

    # Peaceful decay
    assert calc.decay_unrest(50, peace_ticks=2, decay_per_tick=5) == 40
    assert calc.decay_unrest(5, peace_ticks=2, decay_per_tick=5) == 0
