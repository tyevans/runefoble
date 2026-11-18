"""Inventory, equipment slots, and encumbrance calculation tests."""

from __future__ import annotations

from character_sheet.models import (
    CharacterState,
    Encumbrance,
    InventoryItem,
)


def test_encumbrance_threshold_calculations() -> None:
    """Verify dynamic encumbrance tier calculations based on strength capacity."""
    light_items = [InventoryItem(item_id="i1", name="Rations", quantity=10, weight_lbs=2.0)]
    enc_light = Encumbrance.calculate(light_items, strength=10)
    assert enc_light.tier == "light"
    assert enc_light.current_weight_lbs == 20.0
    assert enc_light.capacity_lbs == 150.0

    med_items = [InventoryItem(item_id="i2", name="Chain Mail", quantity=1, weight_lbs=55.0)]
    enc_med = Encumbrance.calculate(med_items, strength=10)
    assert enc_med.tier == "medium"
    assert enc_med.current_weight_lbs == 55.0

    heavy_items = [
        InventoryItem(item_id="i2", name="Chain Mail", quantity=1, weight_lbs=55.0),
        InventoryItem(item_id="i3", name="Anvil", quantity=1, weight_lbs=60.0),
    ]
    enc_heavy = Encumbrance.calculate(heavy_items, strength=10)
    assert enc_heavy.tier == "heavy"
    assert enc_heavy.current_weight_lbs == 115.0

    over_items = [InventoryItem(item_id="i4", name="Massive Boulder", quantity=1, weight_lbs=180.0)]
    enc_over = Encumbrance.calculate(over_items, strength=10)
    assert enc_over.tier == "overburdened"
    assert enc_over.current_weight_lbs == 180.0


def test_equipment_slot_assignments_and_item_transitions(
    sample_character_state: CharacterState,
) -> None:
    """Verify adding, equipping, unequipping, and removing inventory items."""
    with_item = sample_character_state.with_inventory_item(
        item_id="item-greatsword", name="Greatsword", quantity=1, weight_lbs=6.0
    )
    assert "item-greatsword" in with_item.inventory
    assert with_item.inventory["item-greatsword"].quantity == 1

    equipped = with_item.with_equipment_slot("main_hand", "Greatsword")
    assert equipped.equipment["main_hand"] == "Greatsword"

    unequipped = equipped.with_equipment_slot("main_hand", None)
    assert "main_hand" not in unequipped.equipment

    removed = unequipped.without_inventory_item("item-greatsword", 1)
    assert "item-greatsword" not in removed.inventory
