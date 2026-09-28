"""Blackbox tests verifying CharacterAggregate campaign assignment and core attributes.

Complies strictly with:
- ADR-0002: Domain Events via eventsource-py
- ADR-0007: Domain-Driven Design Architecture
- Hard Invariant 1: Object-level authorization runs through SpiceDB Zanzibar schema
- Hard Invariant 2: Domain state transitions flow strictly through DeclarativeAggregate subclasses
- Hard Invariant 6: File length < 500 lines
- Hard Invariant 7: Blackbox TDD with public frontdoors
"""

from uuid import uuid4

import pytest
from character_sheet.aggregate import CharacterAggregate
from character_sheet.dependencies import set_spicedb_client
from character_sheet.main import app
from eventsource.domain.event_registry import default_registry
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_events.events import CharacterAssignedToCampaign
from runefoble_platform.event_sourcing import AggregateRepository, InMemoryEventStore


@pytest.fixture
def mock_spicedb():
    client = MockSpiceDBClient()
    set_spicedb_client(client)
    return client


@pytest.fixture
def client(mock_spicedb):
    return TestClient(app)


def test_character_assigned_to_campaign_event_registry_and_schema():
    """Verify CharacterAssignedToCampaign event is registered, versioned, and CloudEvents compatible."""
    # Check registry resolution
    cls1 = default_registry.get("character.assigned_to_campaign")
    cls2 = default_registry.get("runefoble.events.character.assigned_to_campaign")
    assert cls1 is CharacterAssignedToCampaign
    assert cls2 is CharacterAssignedToCampaign

    # Create event
    char_id = uuid4()
    event = CharacterAssignedToCampaign(
        aggregate_id=char_id,
        character_id=str(char_id),
        campaign_id="camp-underdark-101",
        assigned_by="dm-vance",
    )
    assert event.aggregate_type == "CharacterSheet"
    assert event.event_type == "character.assigned_to_campaign"
    assert getattr(event, "schema_version", None) == 1
    assert event.campaign_id == "camp-underdark-101"
    assert event.assigned_by == "dm-vance"

    # Verify serialization round-trip
    dumped = event.to_dict()
    assert dumped["campaign_id"] == "camp-underdark-101"
    assert dumped["assigned_by"] == "dm-vance"

    rehydrated = CharacterAssignedToCampaign.from_dict(dumped)
    assert rehydrated.aggregate_id == char_id
    assert rehydrated.campaign_id == "camp-underdark-101"
    assert rehydrated.assigned_by == "dm-vance"

    # CloudEvents export
    ce = event.to_cloudevent_dict()
    assert ce["specversion"] == "1.0"
    assert ce["type"] == "runefoble.character.assigned_to_campaign"
    assert ce["source"] == f"/runefoble/charactersheet/{char_id}"
    assert ce["data"]["campaign_id"] == "camp-underdark-101"


@pytest.mark.asyncio
async def test_character_aggregate_core_attributes_and_campaign_mutation():
    """Verify event-sourced CharacterAggregate handles core attributes and campaign assignment."""
    store = InMemoryEventStore()
    repo = AggregateRepository(event_store=store, aggregate_factory=CharacterAggregate)

    char_id = uuid4()
    char = CharacterAggregate(char_id)

    custom_scores = {"str": 16, "dex": 14, "con": 14, "int": 10, "wis": 12, "cha": 8}
    char.create(
        name="Karlach",
        character_class="Barbarian",
        max_hp=48,
        player_id="usr-player-1",
        personality_traits=["fierce", "protective"],
        campaign_id="camp-avernus",
        subclass="Wild Magic",
        armor_class=15,
        speed_ft=35,
        ability_scores=custom_scores,
    )

    # Verify initial state
    assert char.state.name == "Karlach"
    assert char.state.campaign_id == "camp-avernus"
    assert char.state.subclass == "Wild Magic"
    assert char.state.armor_class == 15
    assert char.state.speed_ft == 35
    assert char.state.ability_scores == custom_scores

    # Re-assign campaign
    char.assign_campaign("camp-baldurs-gate", assigned_by="usr-dm-1")
    assert char.state.campaign_id == "camp-baldurs-gate"

    # Unassign campaign
    char.assign_campaign(None, assigned_by="usr-player-1")
    assert char.state.campaign_id is None

    # Save to event store
    await repo.save(char)

    # Reconstitute and verify event replay integrity
    reconstituted = await repo.load(char_id)
    assert reconstituted.state.name == "Karlach"
    assert reconstituted.state.campaign_id is None
    assert reconstituted.state.subclass == "Wild Magic"
    assert reconstituted.state.armor_class == 15
    assert reconstituted.state.speed_ft == 35
    assert reconstituted.state.ability_scores == custom_scores

    # Re-assign on reconstituted aggregate
    reconstituted.assign_campaign("camp-final-battle", assigned_by="usr-dm-1")
    assert reconstituted.state.campaign_id == "camp-final-battle"
    await repo.save(reconstituted)

    final_load = await repo.load(char_id)
    assert final_load.state.campaign_id == "camp-final-battle"


def test_blackbox_character_creation_with_core_attributes(client):
    """Verify frontdoor character creation with core 5e attributes and campaign_id."""
    scores = {"str": 18, "dex": 12, "con": 16, "int": 8, "wis": 10, "cha": 14}
    payload = {
        "name": "Minsc",
        "character_class": "Ranger",
        "max_hp": 52,
        "player_id": "usr-minsc",
        "personality_traits": ["righteous", "hamster-loving"],
        "campaign_id": "camp-rashemen-44",
        "subclass": "Hunter",
        "armor_class": 16,
        "speed_ft": 30,
        "ability_scores": scores,
    }

    create_res = client.post("/api/v1/characters", json=payload)
    assert create_res.status_code == 200
    data = create_res.json()
    char_id = data["character_id"]

    assert data["name"] == "Minsc"
    assert data["campaign_id"] == "camp-rashemen-44"
    assert data["subclass"] == "Hunter"
    assert data["armor_class"] == 16
    assert data["speed_ft"] == 30
    assert data["ability_scores"] == scores

    # GET character through public frontdoor query
    get_res = client.get(f"/api/v1/characters/{char_id}")
    assert get_res.status_code == 200
    fetched = get_res.json()
    assert fetched["character_id"] == char_id
    assert fetched["campaign_id"] == "camp-rashemen-44"
    assert fetched["subclass"] == "Hunter"
    assert fetched["armor_class"] == 16
    assert fetched["speed_ft"] == 30
    assert fetched["ability_scores"] == scores


def test_blackbox_character_campaign_assignment_patch(client):
    """Verify PATCH /api/v1/characters/{character_id}/campaign lifecycle."""
    # 1. Create character without campaign
    create_res = client.post(
        "/api/v1/characters/create",
        json={"name": "Shadowheart", "character_class": "Cleric", "max_hp": 32},
    )
    assert create_res.status_code == 200
    char_id = create_res.json()["character_id"]
    assert create_res.json()["campaign_id"] is None
    assert create_res.json()["subclass"] is None
    assert create_res.json()["armor_class"] == 10
    assert create_res.json()["speed_ft"] == 30
    assert create_res.json()["ability_scores"] == {
        "str": 10,
        "dex": 10,
        "con": 10,
        "int": 10,
        "wis": 10,
        "cha": 10,
    }

    # 2. Assign character to campaign
    patch_res = client.patch(
        f"/api/v1/characters/{char_id}/campaign",
        json={"campaign_id": "camp-shar-cloister", "assigned_by": "dm-viconia"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["campaign_id"] == "camp-shar-cloister"

    # Verify query reflects assigned campaign
    get_res1 = client.get(f"/api/v1/characters/{char_id}")
    assert get_res1.status_code == 200
    assert get_res1.json()["campaign_id"] == "camp-shar-cloister"

    # 3. Re-assign to a different campaign
    patch_res2 = client.patch(
        f"/api/v1/characters/{char_id}/campaign",
        json={"campaign_id": "camp-selune-temple", "assigned_by": "dm-isobel"},
    )
    assert patch_res2.status_code == 200
    assert patch_res2.json()["campaign_id"] == "camp-selune-temple"

    # 4. Unassign character from campaign (campaign_id: null)
    unassign_res = client.patch(
        f"/api/v1/characters/{char_id}/campaign",
        json={"campaign_id": None, "assigned_by": "player-shadowheart"},
    )
    assert unassign_res.status_code == 200
    assert unassign_res.json()["campaign_id"] is None

    # Verify query reflects unassigned status
    get_res2 = client.get(f"/api/v1/characters/{char_id}")
    assert get_res2.status_code == 200
    assert get_res2.json()["campaign_id"] is None


@pytest.mark.asyncio
async def test_blackbox_campaign_assignment_spicedb_authorization(client, mock_spicedb):
    """Verify SpiceDB Zanzibar permissions on campaign assignment endpoint."""
    owner_user = "usr-owner-001"
    unauthorized_user = "usr-stranger-999"

    # Create character owned by owner_user
    create_res = client.post(
        "/api/v1/characters",
        json={
            "name": "Astarion",
            "character_class": "Rogue",
            "max_hp": 28,
            "player_id": owner_user,
        },
        headers={"x-user-id": owner_user},
    )
    assert create_res.status_code == 200
    char_id = create_res.json()["character_id"]

    # Write explicit owner relation in mock SpiceDB
    await mock_spicedb.write_relationship("character", char_id, "owner", "user", owner_user)

    # Attempt to assign campaign as unauthorized user -> 403 Forbidden
    unauth_patch = client.patch(
        f"/api/v1/characters/{char_id}/campaign",
        json={"campaign_id": "camp-cazador"},
        headers={"x-user-id": unauthorized_user},
    )
    assert unauth_patch.status_code == 403
    assert "does not have edit permission" in unauth_patch.json()["detail"]

    # Authorized user (owner) can assign campaign -> 200 OK
    auth_patch = client.patch(
        f"/api/v1/characters/{char_id}/campaign",
        json={"campaign_id": "camp-cazador"},
        headers={"x-user-id": owner_user},
    )
    assert auth_patch.status_code == 200
    assert auth_patch.json()["campaign_id"] == "camp-cazador"

    # Verify SpiceDB relationship was written
    rels = await mock_spicedb.read_relationships(
        resource_type="character", resource_id=char_id, relation="campaign"
    )
    assert any(r.subject_id == "camp-cazador" for r in rels)

    # Authorized user unassigns campaign
    unassign_patch = client.patch(
        f"/api/v1/characters/{char_id}/campaign",
        json={"campaign_id": None},
        headers={"x-user-id": owner_user},
    )
    assert unassign_patch.status_code == 200
    assert unassign_patch.json()["campaign_id"] is None

    # Verify SpiceDB campaign relationship was deleted
    rels_after = await mock_spicedb.read_relationships(
        resource_type="character", resource_id=char_id, relation="campaign"
    )
    assert len(rels_after) == 0
