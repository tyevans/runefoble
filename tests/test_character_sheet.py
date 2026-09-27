"""Comprehensive unit and integration tests for decomposed CharacterAggregate and modular handlers."""

from pathlib import Path
from uuid import uuid4

import pytest
from character_sheet.aggregate import (
    CLASS_HIT_DIE,
    KNOWN_SPELL_LEVELS,
    SPELL_SLOTS_TABLE,
    CharacterAggregate,
    CharacterSheetState,
    CharacterState,
    ConditionState,
    InventoryHandlerMixin,
    InventoryItem,
    SpellsHandlerMixin,
    StandInGuardrails,
    VitalsHandlerMixin,
    get_hit_die_for_class,
    get_known_spell_level,
    get_spell_slots_for_level,
)
from runefoble_events.events import (
    CharacterCreated,
    CharacterHealthChanged,
    ConditionApplied,
    StandInStabilized,
)
from runefoble_platform.event_sourcing import AggregateRepository, InMemoryEventStore

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_character_aggregate_exports_backward_compatibility():
    """Verify all symbols and rules functions remain exported from character_sheet.aggregate."""
    assert issubclass(CharacterAggregate, InventoryHandlerMixin)
    assert issubclass(CharacterAggregate, SpellsHandlerMixin)
    assert issubclass(CharacterAggregate, VitalsHandlerMixin)
    assert CharacterState is not None
    assert CharacterSheetState is not None
    assert ConditionState is not None
    assert InventoryItem is not None
    assert StandInGuardrails is not None
    assert isinstance(CLASS_HIT_DIE, dict)
    assert isinstance(KNOWN_SPELL_LEVELS, dict)
    assert isinstance(SPELL_SLOTS_TABLE, dict)
    assert callable(get_hit_die_for_class)
    assert callable(get_known_spell_level)
    assert callable(get_spell_slots_for_level)


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


def test_character_sheet_decomposed_file_length_invariants():
    """Enforce strict line limits on decomposed handlers (<150 lines) and aggregate (<120 lines)."""
    cs_dir = REPO_ROOT / "services" / "character_sheet" / "src" / "character_sheet"
    handlers_dir = cs_dir / "handlers"

    aggregate_py = cs_dir / "aggregate.py"
    inventory_py = handlers_dir / "inventory.py"
    spells_py = handlers_dir / "spells.py"
    vitals_py = handlers_dir / "vitals.py"
    init_py = handlers_dir / "__init__.py"

    assert aggregate_py.exists()
    assert inventory_py.exists()
    assert spells_py.exists()
    assert vitals_py.exists()
    assert init_py.exists()

    aggregate_lines = len(aggregate_py.read_text().splitlines())
    inventory_lines = len(inventory_py.read_text().splitlines())
    spells_lines = len(spells_py.read_text().splitlines())
    vitals_lines = len(vitals_py.read_text().splitlines())

    assert aggregate_lines < 120, f"aggregate.py has {aggregate_lines} lines; must be < 120 lines"
    assert inventory_lines < 120, f"inventory.py has {inventory_lines} lines; must be < 120 lines"
    assert spells_lines < 120, f"spells.py has {spells_lines} lines; must be < 120 lines"
    assert vitals_lines < 140, f"vitals.py has {vitals_lines} lines; must be < 140 lines"

    # Hard Invariant 6: All files strictly under 500 lines
    for f in list(cs_dir.glob("*.py")) + list(handlers_dir.glob("*.py")):
        lines = len(f.read_text().splitlines())
        assert lines < 500, (
            f"File {f.name} violates Hard Invariant 6 with {lines} lines (>500 limit)"
        )
