"""Level progression, spell progression, and spell slot models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SpellProgression(BaseModel):
    level: int = 1
    xp: int = 0
    spell_slots: dict[int, int] = Field(default_factory=lambda: {1: 2})
    spellbook: list[str] = Field(default_factory=list)
    prepared_spells: list[str] = Field(default_factory=list)


class LevelProgression(BaseModel):
    current_level: int = 1
    current_xp: int = 0
    next_level_xp: int = 300
    hit_die: str = "d8"
    max_hp_increase: int = 0


class ProgressionTransitionsMixin:
    """Transition methods for level advancement and spell slot management."""

    def with_level_up(
        self: Any, new_level: int, max_hp_increase: int, spell_slots: dict[int, int]
    ) -> Any:
        return self.model_copy(
            update={
                "level": new_level,
                "max_hp": self.max_hp + max_hp_increase,
                "current_hp": self.current_hp + max_hp_increase,
                "spell_slots": spell_slots,
            }
        )

    def with_prepared_spell(self: Any, spell_name: str) -> Any:
        prep = list(self.prepared_spells)
        if spell_name not in prep:
            prep.append(spell_name)
        book = list(self.spellbook)
        if spell_name not in book:
            book.append(spell_name)
        return self.model_copy(update={"prepared_spells": prep, "spellbook": book})

    def without_prepared_spell(self: Any, spell_name: str) -> Any:
        prep = [s for s in self.prepared_spells if s != spell_name]
        return self.model_copy(update={"prepared_spells": prep})

    def with_expended_spell_slot(self: Any, slot_level: int, remaining: int) -> Any:
        slots = dict(self.spell_slots)
        slots[slot_level] = remaining
        return self.model_copy(update={"spell_slots": slots})
