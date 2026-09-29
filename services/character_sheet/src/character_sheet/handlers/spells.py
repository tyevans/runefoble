"""Spellbook and character progression mutation handlers and event reducers."""

from typing import Any

from character_sheet.models import CharacterState
from character_sheet.rules import (
    get_hit_die_for_class,
    get_known_spell_level,
    get_spell_slots_for_level,
)
from eventsource.domain.decorators import handles
from runefoble_events.events import (
    CharacterLeveledUp,
    SpellPrepared,
    SpellSlotExpended,
)


class SpellsHandlerMixin:
    """Mixin providing spell preparation, slot expenditure, and level progression."""

    _state: CharacterState | None
    state: CharacterState
    create_event: Any
    aggregate_id: Any

    def level_up(
        self,
        target_level: int | None = None,
        hp_increase: int | None = None,
        session_id: str = "",
    ) -> None:
        """Advance character level, increase hit points, and scale spell slots."""
        new_level = target_level if target_level is not None else self.state.level + 1
        if hp_increase is None:
            hp_increase = get_hit_die_for_class(self.state.character_class)
        spell_slots = get_spell_slots_for_level(new_level, self.state.spell_slots)
        self.create_event(
            CharacterLeveledUp,
            session_id=session_id,
            character_id=str(self.aggregate_id),
            new_level=new_level,
            max_hp_increase=hp_increase,
            spell_slots=spell_slots,
        )

    def prepare_spell(
        self, spell_name: str, spell_level: int | None = None, session_id: str = ""
    ) -> None:
        """Prepare a spell in the character's active spellbook."""
        if spell_level is None or spell_level <= 0:
            spell_level = get_known_spell_level(spell_name)
        self.create_event(
            SpellPrepared,
            session_id=session_id,
            character_id=str(self.aggregate_id),
            spell_name=spell_name,
            spell_level=spell_level,
        )

    def unprepare_spell(self, spell_name: str) -> None:
        """Unprepare a spell from the character's active spellbook."""
        self._state = self.state.without_prepared_spell(spell_name)

    def cast_spell(
        self, spell_name: str, slot_level: int | None = None, session_id: str = ""
    ) -> None:
        """Cast a prepared spell, expending an appropriate level spell slot."""
        if slot_level is None or slot_level <= 0:
            slot_level = get_known_spell_level(spell_name)
        available_slots = self.state.spell_slots.get(slot_level, 0)
        if available_slots <= 0:
            raise ValueError(
                f"INSUFFICIENT_SPELL_SLOTS: Character '{self.aggregate_id}' has 0 level {slot_level} spell slots remaining to cast '{spell_name}'"
            )
        if self.state.is_stand_in_active:
            preserve_count = self.state.stand_in_guardrails.preserve_spell_slots.get(slot_level, 0)
            if available_slots <= preserve_count:
                raise ValueError(
                    f"STAND_IN_GUARDRAIL_VIOLATION: Character '{self.aggregate_id}' has {available_slots} level {slot_level} spell slots, but stand-in tactical policy reserves {preserve_count} slot(s)."
                )
        self.create_event(
            SpellSlotExpended,
            session_id=session_id,
            character_id=str(self.aggregate_id),
            spell_name=spell_name,
            slot_level_used=slot_level,
            remaining_slots=available_slots - 1,
        )

    @handles(CharacterLeveledUp)
    def _on_leveled_up(self, event: CharacterLeveledUp) -> None:
        self._state = self.state.with_level_up(
            new_level=event.new_level,
            max_hp_increase=event.max_hp_increase,
            spell_slots=event.spell_slots,
        )

    @handles(SpellPrepared)
    def _on_spell_prepared(self, event: SpellPrepared) -> None:
        self._state = self.state.with_prepared_spell(event.spell_name)

    @handles(SpellSlotExpended)
    def _on_spell_slot_expended(self, event: SpellSlotExpended) -> None:
        self._state = self.state.with_expended_spell_slot(
            slot_level=event.slot_level_used, remaining=event.remaining_slots
        )
