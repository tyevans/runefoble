"""Event-sourced CharacterSheet aggregate using eventsource-py and modular handlers."""

from character_sheet.handlers import (
    InventoryHandlerMixin,
    SpellsHandlerMixin,
    VitalsHandlerMixin,
)
from character_sheet.models import (
    CharacterSheetState,
    CharacterState,
    ConditionState,
    InventoryItem,
    StandInGuardrails,
)
from character_sheet.rules import (
    CLASS_HIT_DIE,
    KNOWN_SPELL_LEVELS,
    SPELL_SLOTS_TABLE,
    get_hit_die_for_class,
    get_known_spell_level,
    get_spell_slots_for_level,
)
from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from runefoble_events.events import CharacterCreated

__all__ = [
    "CLASS_HIT_DIE",
    "KNOWN_SPELL_LEVELS",
    "SPELL_SLOTS_TABLE",
    "CharacterAggregate",
    "CharacterSheetState",
    "CharacterState",
    "ConditionState",
    "InventoryHandlerMixin",
    "InventoryItem",
    "SpellsHandlerMixin",
    "StandInGuardrails",
    "VitalsHandlerMixin",
    "get_hit_die_for_class",
    "get_known_spell_level",
    "get_spell_slots_for_level",
]


class CharacterAggregate(
    InventoryHandlerMixin,
    SpellsHandlerMixin,
    VitalsHandlerMixin,
    DeclarativeAggregate[CharacterState],
):
    """Event-sourced aggregate managing character stats, equipment, inventory, and conditions."""

    aggregate_type = "CharacterSheet"
    requires_creation_event = True

    def create(
        self,
        name: str,
        character_class: str,
        max_hp: int = 30,
        player_id: str | None = None,
        personality_traits: list[str] | None = None,
    ) -> None:
        """Create a new character."""
        self.create_event(
            CharacterCreated,
            session_id=None,
            name=name,
            character_class=character_class,
            max_hp=max_hp,
            current_hp=max_hp,
            player_id=player_id,
            personality_traits=personality_traits or ["brave", "curious"],
        )

    @handles(CharacterCreated)
    def _on_created(self, event: CharacterCreated) -> None:
        self._state = CharacterState.initial(
            character_id=event.aggregate_id,
            name=event.name,
            character_class=event.character_class,
            max_hp=event.max_hp,
            current_hp=event.current_hp,
            player_id=event.player_id,
            personality_traits=event.personality_traits,
        )
