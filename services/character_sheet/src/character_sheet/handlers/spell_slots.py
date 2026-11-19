"""Spell slot restoration handler mixin and event applier for CharacterAggregate."""

from typing import Any

from character_sheet.models import CharacterState
from character_sheet.rules import get_spell_slots_max
from eventsource.domain.decorators import handles
from runefoble_events.events import SpellSlotsRestored
from runefoble_platform.domain_errors import DomainRefusedError


class SpellSlotRestoreHandlerMixin:
    """Mixin providing restoration of spent spell slots to their maximum."""

    _state: CharacterState | None
    state: CharacterState
    create_event: Any
    aggregate_id: Any

    def restore_spell_slots(self, slot_level: int | None = None, session_id: str = "") -> None:
        """Restore spent spell slots to their maximum for the character's level.

        Without slot_level, every level returns to its maximum. With slot_level, only that
        level is restored. The event carries the full resulting slot map so replay is absolute.
        """
        maximum = get_spell_slots_max(self.state.level)
        if slot_level is not None and slot_level not in maximum:
            raise DomainRefusedError(
                f"INVALID_SPELL_SLOT_LEVEL: Character '{self.aggregate_id}' at level {self.state.level} has no level {slot_level} spell slots."
            )
        slots = dict(self.state.spell_slots)
        for level, max_count in maximum.items():
            if slot_level is None or level == slot_level:
                slots[level] = max_count
        self.create_event(
            SpellSlotsRestored,
            session_id=session_id,
            character_id=str(self.aggregate_id),
            slot_level=slot_level,
            spell_slots=slots,
        )

    @handles(SpellSlotsRestored)
    def _on_spell_slots_restored(self, event: SpellSlotsRestored) -> None:
        self._state = self.state.with_restored_spell_slots(event.spell_slots)
