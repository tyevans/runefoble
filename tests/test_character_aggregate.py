"""Unit and integration tests for CharacterAggregate and character_sheet service."""

from uuid import uuid4

import pytest
from character_sheet.aggregate import CharacterAggregate
from character_sheet.main import app
from eventsource.domain.event_registry import default_registry
from fastapi.testclient import TestClient
from runefoble_events.events import CharacterAssignedToCampaign
from runefoble_platform.event_sourcing import AggregateRepository, InMemoryEventStore

from tests.helpers.ws_identity import bearer

client = TestClient(app, headers=bearer("character-owner"))


@pytest.mark.asyncio
async def test_character_aggregate_inventory_and_equipment():
    """Verify event-sourced inventory and equipment management."""
    store = InMemoryEventStore()
    repo = AggregateRepository(event_store=store, aggregate_factory=CharacterAggregate)

    char_id = uuid4()
    char = CharacterAggregate(char_id)
    char.create(name="Valeros", character_class="Fighter", max_hp=45)

    # Add items
    char.add_inventory_item("item-1", name="Healing Potion", quantity=3, weight_lbs=1.5)
    char.add_inventory_item("item-2", name="Rations", quantity=5, weight_lbs=10.0)
    assert len(char.state.inventory) == 2
    assert char.state.inventory["item-1"].quantity == 3

    # Remove 1 healing potion
    char.remove_inventory_item("item-1", quantity=1)
    assert char.state.inventory["item-1"].quantity == 2

    # Equip weapon and armor
    char.equip_item("main_hand", "Longsword +1")
    char.equip_item("armor", "Plate Mail")
    assert char.state.equipment["main_hand"] == "Longsword +1"
    assert char.state.equipment["armor"] == "Plate Mail"

    # Apply condition
    char.apply_condition("blinded", duration_rounds=2, source="Darkness spell")
    assert "blinded" in char.state.conditions
    assert char.state.conditions["blinded"].duration_rounds == 2

    # Save to event store
    await repo.save(char)

    # Reconstitute and verify
    reconstituted = await repo.load(char_id)
    assert reconstituted.state.name == "Valeros"
    assert reconstituted.state.inventory["item-1"].quantity == 2
    assert reconstituted.state.equipment["main_hand"] == "Longsword +1"
    assert "blinded" in reconstituted.state.conditions

    # Clear condition
    reconstituted.remove_condition("blinded")
    assert "blinded" not in reconstituted.state.conditions


def test_character_endpoints():
    """Verify REST endpoints for character inventory, equipment, and conditions."""
    # 1. Create character
    res = client.post(
        "/api/v1/characters",
        json={"name": "Ezren", "character_class": "Wizard", "max_hp": 22},
    )
    assert res.status_code == 200
    char_id = res.json()["character_id"]

    # 2. Add inventory item
    res_inv = client.post(
        f"/api/v1/characters/{char_id}/inventory",
        json={"item_id": "spellbook", "name": "Arcane Spellbook", "quantity": 1, "weight_lbs": 3.0},
    )
    assert res_inv.status_code == 200
    assert "spellbook" in res_inv.json()["inventory"]

    # 3. Equip item
    res_eq = client.post(
        f"/api/v1/characters/{char_id}/equipment",
        json={"slot": "main_hand", "item_name": "Quarterstaff"},
    )
    assert res_eq.status_code == 200
    assert res_eq.json()["equipment"]["main_hand"] == "Quarterstaff"

    # 4. Apply condition
    res_cond = client.post(
        f"/api/v1/characters/{char_id}/conditions",
        json={"condition": "prone", "source": "Tripped by goblin"},
    )
    assert res_cond.status_code == 200
    assert "prone" in res_cond.json()["conditions"]

    # 5. Remove condition
    res_del_cond = client.delete(f"/api/v1/characters/{char_id}/conditions/prone")
    assert res_del_cond.status_code == 200
    assert "prone" not in res_del_cond.json()["conditions"]


def test_character_aggregate_stand_in_guardrails_spell_preservation():
    """Verify that Stand-in AI is blocked from expending reserved spell slots."""
    char_id = uuid4()
    char = CharacterAggregate(char_id)
    char.create(name="Kyra", character_class="Cleric", max_hp=30)
    # Prepared spells and slots
    char.prepare_spell("Cure Wounds", spell_level=1)
    # Set stand in guardrail: preserve 2 level-1 slots
    char.update_stand_in_guardrails({"preserve_spell_slots": {1: 2}})
    char.set_stand_in_active(True)

    # Attempting to cast spell when available_slots (2) <= preserve_count (2) raises ValueError
    with pytest.raises(ValueError, match="STAND_IN_GUARDRAIL_VIOLATION"):
        char.cast_spell("Cure Wounds", slot_level=1)


def test_unit_character_assigned_event_registry_and_schema():
    """Verify CharacterAssignedToCampaign event is registered, versioned, and CloudEvents compatible."""
    # Check registry resolution
    cls1 = default_registry.get("runefoble.events.character.assigned_to_campaign")
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
    assert event.event_type == "runefoble.events.character.assigned_to_campaign"
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
    assert ce["type"] == "runefoble.events.character.assigned_to_campaign"
    assert ce["source"] == f"/runefoble/charactersheet/{char_id}"
    assert ce["data"]["campaign_id"] == "camp-underdark-101"


@pytest.mark.asyncio
async def test_unit_character_aggregate_campaign_mutation_round_trip():
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
