"""CharacterSheet aggregate events."""

from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event("runefoble.events.character.created")
class CharacterCreated(BaseRunefobleEvent):
    event_type: str = "runefoble.events.character.created"

    aggregate_type: str = "CharacterSheet"
    name: str
    character_class: str
    max_hp: int
    current_hp: int
    player_id: str | None = None
    campaign_id: UUID | str = ""
    personality_traits: list[str] = Field(default_factory=list)
    subclass: str | None = None
    armor_class: int = 10
    speed_ft: int = 30
    ability_scores: dict[str, int] = Field(
        default_factory=lambda: {
            "str": 10,
            "dex": 10,
            "con": 10,
            "int": 10,
            "wis": 10,
            "cha": 10,
        }
    )


@register_event("runefoble.events.character.health_changed")
class CharacterHealthChanged(BaseRunefobleEvent):
    """HP change for one character. session_id is None when no session is in play."""

    event_type: str = "runefoble.events.character.health_changed"

    aggregate_type: str = "CharacterSheet"
    session_id: str | None = None
    campaign_id: str | None = None
    delta: int
    current_hp: int
    max_hp: int
    source: str = "damage"


@register_event("runefoble.events.character.absence_penalty_applied")
class AbsencePenaltyApplied(BaseRunefobleEvent):
    event_type: str = "runefoble.events.character.absence_penalty_applied"

    aggregate_type: str = "CharacterSheet"
    penalty_type: Literal["drunk", "foolishness", "cowardice", "greed", "curse"]
    description: str
    imposed_by: Literal["human_dm", "the_watcher"] = "the_watcher"


@register_event("runefoble.events.character.absence_penalty_cleared")
class AbsencePenaltyCleared(BaseRunefobleEvent):
    event_type: str = "runefoble.events.character.absence_penalty_cleared"

    aggregate_type: str = "CharacterSheet"
    penalty_type: str


@register_event("runefoble.events.character.item_added_to_inventory")
class ItemAddedToInventory(BaseRunefobleEvent):
    event_type: str = "runefoble.events.character.item_added_to_inventory"

    aggregate_type: str = "CharacterSheet"
    item_id: str
    name: str
    quantity: int = 1
    weight_lbs: float = 0.0


@register_event("runefoble.events.character.item_removed_from_inventory")
class ItemRemovedFromInventory(BaseRunefobleEvent):
    event_type: str = "runefoble.events.character.item_removed_from_inventory"

    aggregate_type: str = "CharacterSheet"
    item_id: str
    quantity: int = 1


@register_event("runefoble.events.character.equipment_slot_updated")
class EquipmentSlotUpdated(BaseRunefobleEvent):
    event_type: str = "runefoble.events.character.equipment_slot_updated"

    aggregate_type: str = "CharacterSheet"
    slot: str
    item_name: str | None = None


@register_event("runefoble.events.character.condition_applied")
class ConditionApplied(BaseRunefobleEvent):
    event_type: str = "runefoble.events.character.condition_applied"

    aggregate_type: str = "CharacterSheet"
    condition: str
    duration_rounds: int | None = None
    source: str = ""


@register_event("runefoble.events.character.condition_removed")
class ConditionRemoved(BaseRunefobleEvent):
    event_type: str = "runefoble.events.character.condition_removed"

    aggregate_type: str = "CharacterSheet"
    condition: str


@register_event("runefoble.events.character.leveled_up")
class CharacterLeveledUp(BaseRunefobleEvent):
    aggregate_type: str = "CharacterSheet"
    event_type: str = "runefoble.events.character.leveled_up"
    session_id: str = ""
    character_id: str
    new_level: int
    max_hp_increase: int
    spell_slots: dict[int, int] = Field(default_factory=dict)


@register_event("runefoble.events.character.spell_prepared")
class SpellPrepared(BaseRunefobleEvent):
    aggregate_type: str = "CharacterSheet"
    event_type: str = "runefoble.events.character.spell_prepared"
    session_id: str = ""
    character_id: str
    spell_name: str
    spell_level: int


@register_event("runefoble.events.character.spell_slot_expended")
class SpellSlotExpended(BaseRunefobleEvent):
    aggregate_type: str = "CharacterSheet"
    event_type: str = "runefoble.events.character.spell_slot_expended"
    session_id: str = ""
    character_id: str
    spell_name: str
    slot_level_used: int
    remaining_slots: int


@register_event("runefoble.events.character.spell_slots_restored")
class SpellSlotsRestored(BaseRunefobleEvent):
    aggregate_type: str = "CharacterSheet"
    event_type: str = "runefoble.events.character.spell_slots_restored"
    session_id: str = ""
    character_id: str
    slot_level: int | None = None
    spell_slots: dict[int, int] = Field(default_factory=dict)


@register_event("runefoble.events.character.spell_unprepared")
class SpellUnprepared(BaseRunefobleEvent):
    aggregate_type: str = "CharacterSheet"
    event_type: str = "runefoble.events.character.spell_unprepared"
    session_id: str = ""
    character_id: str
    spell_name: str


@register_event("runefoble.events.character.stand_in_policy_updated")
class StandInPolicyUpdated(BaseRunefobleEvent):
    aggregate_type: str = "CharacterSheet"
    event_type: str = "runefoble.events.character.stand_in_policy_updated"
    character_id: UUID | str
    guardrails: dict[str, Any] = Field(default_factory=dict)


@register_event("runefoble.events.character.stand_in_stabilized")
class StandInStabilized(BaseRunefobleEvent):
    aggregate_type: str = "CharacterSheet"
    event_type: str = "runefoble.events.character.stand_in_stabilized"
    character_id: UUID | str
    current_hp: int = 0
    condition: str = "unconscious_stabilized"


@register_event("runefoble.events.character.stand_in_activated")
class StandInActivated(BaseRunefobleEvent):
    aggregate_type: str = "CharacterSheet"
    event_type: str = "runefoble.events.character.stand_in_activated"
    session_id: str = ""
    character_id: UUID | str


@register_event("runefoble.events.character.stand_in_released")
class StandInReleased(BaseRunefobleEvent):
    aggregate_type: str = "CharacterSheet"
    event_type: str = "runefoble.events.character.stand_in_released"
    session_id: str = ""
    character_id: UUID | str


@register_event("runefoble.events.character.damaged")
class CharacterDamaged(BaseRunefobleEvent):
    """Emitted when a character takes damage, reducing hit points."""

    aggregate_type: str = "CharacterSheet"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.character.damaged"
    character_id: UUID | str
    delta: int  # negative value
    current_hp: int
    max_hp: int
    source: str = "damage"


@register_event("runefoble.events.character.portrait_variant_generated")
class PortraitVariantGenerated(BaseRunefobleEvent):
    """Emitted when a generative wardrobe attire variation is synthesized."""

    aggregate_type: str = "CharacterSheet"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.character.portrait_variant_generated"
    character_id: UUID | str
    variant_id: str
    variant_name: str
    attire_type: str
    image_url: str
    prompt: str = ""
    is_active: bool = False
    created_at: str = ""


@register_event("runefoble.events.character.portrait_updated")
class CharacterPortraitUpdated(BaseRunefobleEvent):
    """Emitted when a character's active portrait or token avatar is assigned."""

    aggregate_type: str = "CharacterSheet"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.character.portrait_updated"
    character_id: UUID | str
    active_portrait_url: str | None
    variant_id: str | None = None


# Backward-compatible alias


@register_event("runefoble.events.character.assigned_to_campaign", schema_version=1)
class CharacterAssignedToCampaign(BaseRunefobleEvent):
    """Emitted when a character is assigned to or unassigned from a campaign."""

    event_type: str = "runefoble.events.character.assigned_to_campaign"
    aggregate_type: str = "CharacterSheet"
    aggregate_id: UUID = Field(default_factory=uuid4)
    character_id: str = ""
    campaign_id: str | None = None
    assigned_by: str = ""
