"""Unit and integration tests for CharacterAggregate and character_sheet service."""

from uuid import uuid4

import pytest
from character_sheet.aggregate import CharacterAggregate
from character_sheet.main import app
from fastapi.testclient import TestClient
from runefoble_platform.event_sourcing import AggregateRepository, InMemoryEventStore

client = TestClient(app)


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
        "/api/v1/characters/create",
        json={"name": "Ezren", "character_class": "Wizard", "max_hp": 22},
    )
    assert res.status_code == 200
    char_id = res.json()["character_id"]

    # 2. Add inventory item
    res_inv = client.post(
        f"/api/v1/characters/{char_id}/inventory/add",
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
