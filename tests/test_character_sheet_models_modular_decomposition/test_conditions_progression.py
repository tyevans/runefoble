"""Conditions, penalties, spell slots, and level progression tests."""

from __future__ import annotations

from character_sheet.models import (
    CharacterState,
    ConditionModifier,
)


def test_condition_and_penalty_transitions(sample_character_state: CharacterState) -> None:
    """Verify condition application/removal, penalties, and condition modifier modeling."""
    cond_state = sample_character_state.with_condition(
        "blinded", duration_rounds=3, source="flashbang"
    )
    assert "blinded" in cond_state.conditions
    assert cond_state.conditions["blinded"].duration_rounds == 3

    uncond_state = cond_state.without_condition("blinded")
    assert "blinded" not in uncond_state.conditions

    pen_state = sample_character_state.with_penalty("drunk", "DM imposed drunkenness penalty")
    assert "drunk" in pen_state.penalties
    unpen_state = pen_state.without_penalty("drunk")
    assert "drunk" not in unpen_state.penalties

    mod = ConditionModifier(
        condition="exhaustion",
        effect_type="tactical",
        description="disadvantage on ability checks",
        disadvantage_checks=["ability_checks"],
        speed_penalty_ft=10,
    )
    assert mod.condition == "exhaustion"
    assert mod.effect_type == "tactical"
    assert mod.disadvantage_checks == ["ability_checks"]
    assert mod.speed_penalty_ft == 10


def test_level_up_and_spell_progression(sample_character_state: CharacterState) -> None:
    """Verify level progression, spell preparation, and slot expenditure."""
    damaged_state = sample_character_state.with_health(25)
    level_state = damaged_state.with_level_up(2, max_hp_increase=10, spell_slots={1: 3})
    assert level_state.level == 2
    assert level_state.max_hp == 50
    assert level_state.current_hp == 35
    assert level_state.spell_slots == {1: 3}

    spell_state = level_state.with_prepared_spell("Cure Wounds")
    assert "Cure Wounds" in spell_state.prepared_spells
    assert "Cure Wounds" in spell_state.spellbook

    expended_state = spell_state.with_expended_spell_slot(1, 2)
    assert expended_state.spell_slots[1] == 2
