"""Comprehensive unit and integration tests for decomposed CharacterAggregate and modular handlers."""

from uuid import uuid4

import pytest
from character_sheet.aggregate import (
    CharacterAggregate,
)
from runefoble_events.events import (
    CharacterCreated,
    CharacterHealthChanged,
    ConditionApplied,
    StandInStabilized,
)
from runefoble_platform.event_sourcing import AggregateRepository, InMemoryEventStore


@pytest.mark.asyncio
async def test_character_aggregate_lifecycle_and_reconstitution():
    """Verify event-sourced aggregate operations across inventory, spells, vitals, and reconstitution."""
    store = InMemoryEventStore()
    repo = AggregateRepository(event_store=store, aggregate_factory=CharacterAggregate)

    char_id = uuid4()
    char = CharacterAggregate(char_id)
    char.create(name="Faelar", character_class="Ranger", max_hp=32)

    # 1. Inventory & Equipment mutations
    char.add_inventory_item("bow-1", name="Longbow", quantity=1, weight_lbs=2.0)
    char.add_inventory_item("arrow-1", name="Arrows (20)", quantity=2, weight_lbs=3.0)
    assert len(char.state.inventory) == 2
    char.equip_item("main_hand", "Longbow")
    assert char.state.equipment["main_hand"] == "Longbow"
    char.remove_inventory_item("arrow-1", quantity=1)
    assert char.state.inventory["arrow-1"].quantity == 1

    # 2. Vitals & Conditions
    char.modify_health(-10, source="Goblin Arrow")
    assert char.state.current_hp == 22
    char.apply_condition("poisoned", duration_rounds=3, source="Poison Tip")
    assert "poisoned" in char.state.conditions
    char.apply_penalty("foolishness", description="Rushed ahead", imposed_by="the_watcher")
    assert "foolishness" in char.state.penalties

    # 3. Spells & Progression
    char.level_up(target_level=2, hp_increase=10)
    assert char.state.level == 2
    assert char.state.max_hp == 42
    char.prepare_spell("Hunter's Mark", spell_level=1)
    assert "Hunter's Mark" in char.state.prepared_spells
    char.cast_spell("Hunter's Mark", slot_level=1)

    # Save to store and reload
    await repo.save(char)
    reconstituted = await repo.load(char_id)

    assert reconstituted.state.name == "Faelar"
    assert reconstituted.state.level == 2
    assert reconstituted.state.current_hp == 32
    assert reconstituted.state.equipment["main_hand"] == "Longbow"
    assert reconstituted.state.inventory["arrow-1"].quantity == 1
    assert "poisoned" in reconstituted.state.conditions
    assert "foolishness" in reconstituted.state.penalties
    assert "Hunter's Mark" in reconstituted.state.prepared_spells

    # Cleanup actions on reconstituted instance
    reconstituted.remove_condition("poisoned")
    assert "poisoned" not in reconstituted.state.conditions
    reconstituted.clear_penalty("foolishness")
    assert "foolishness" not in reconstituted.state.penalties


def test_stand_in_permadeath_safeguard():
    """Verify zero-HP permadeath safeguard triggers unconscious_stabilized for stand-ins."""
    char_id = uuid4()
    char = CharacterAggregate(char_id)
    char.create(name="Seoni", character_class="Sorcerer", max_hp=20)
    char.set_stand_in_active(True)

    # Inflict lethal damage
    char.modify_health(-30, source="Dragon Breath")
    assert char.state.current_hp == 0
    assert "unconscious_stabilized" in char.state.conditions

    # Verify emitted events
    events = [type(e) for e in char.uncommitted_events]
    assert CharacterCreated in events
    assert CharacterHealthChanged in events
    assert StandInStabilized in events
    assert ConditionApplied in events
