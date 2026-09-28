"""Event-sourced CharacterSheet aggregate using eventsource-py and modular handlers."""

from character_sheet.handlers import (
    InventoryHandlerMixin,
    PortraitHandlerMixin,
    SpellsHandlerMixin,
    VitalsHandlerMixin,
)
from character_sheet.models import (
    CharacterSheetState,
    CharacterState,
    ConditionState,
    InventoryItem,
    StandInGuardrails,
    WardrobeVariant,
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
from runefoble_events.events import CharacterAssignedToCampaign, CharacterCreated

DEFAULT_SCORES = {"str": 10, "dex": 10, "con": 10, "int": 10, "wis": 10, "cha": 10}

# fmt: off
__all__ = [
    "CLASS_HIT_DIE", "KNOWN_SPELL_LEVELS", "SPELL_SLOTS_TABLE", "CharacterAggregate",
    "CharacterSheetState", "CharacterState", "ConditionState", "InventoryHandlerMixin",
    "InventoryItem", "PortraitHandlerMixin", "SpellsHandlerMixin", "StandInGuardrails",
    "VitalsHandlerMixin", "WardrobeVariant", "get_hit_die_for_class",
    "get_known_spell_level", "get_spell_slots_for_level",
]
# fmt: on


class CharacterAggregate(
    InventoryHandlerMixin,
    SpellsHandlerMixin,
    VitalsHandlerMixin,
    PortraitHandlerMixin,
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
        campaign_id: str | None = None,
        subclass: str | None = None,
        armor_class: int = 10,
        speed_ft: int = 30,
        ability_scores: dict[str, int] | None = None,
    ) -> None:
        """Create a new character."""
        scores = dict(ability_scores) if ability_scores is not None else dict(DEFAULT_SCORES)
        self.create_event(
            CharacterCreated,
            session_id=None,
            name=name,
            character_class=character_class,
            max_hp=max_hp,
            current_hp=max_hp,
            player_id=player_id,
            personality_traits=personality_traits or ["brave", "curious"],
            campaign_id=campaign_id or "",
            subclass=subclass,
            armor_class=armor_class,
            speed_ft=speed_ft,
            ability_scores=scores,
        )

    @handles(CharacterCreated)
    def _on_created(self, event: CharacterCreated) -> None:
        camp = str(event.campaign_id) if getattr(event, "campaign_id", None) else None
        self._state = CharacterState.initial(
            character_id=event.aggregate_id,
            name=event.name,
            character_class=event.character_class,
            max_hp=event.max_hp,
            current_hp=event.current_hp,
            player_id=event.player_id,
            personality_traits=event.personality_traits,
            campaign_id=camp,
            subclass=getattr(event, "subclass", None),
            armor_class=getattr(event, "armor_class", 10),
            speed_ft=getattr(event, "speed_ft", 30),
            ability_scores=getattr(event, "ability_scores", None),
        )

    def assign_campaign(self, campaign_id: str | None, assigned_by: str) -> None:
        """Assign or unassign character to/from a campaign party."""
        self.create_event(
            CharacterAssignedToCampaign,
            character_id=str(self.aggregate_id),
            campaign_id=campaign_id,
            assigned_by=assigned_by,
        )

    @handles(CharacterAssignedToCampaign)
    def _on_campaign_assigned(self, event: CharacterAssignedToCampaign) -> None:
        self._state = self._state.with_campaign(
            str(event.campaign_id) if event.campaign_id is not None else None
        )
