"""CharacterSheet aggregate events."""

from typing import Any, ClassVar, Literal
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event
class CharacterCreated(BaseRunefobleEvent):
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


@register_event
class CharacterHealthChanged(BaseRunefobleEvent):
    aggregate_type: str = "CharacterSheet"
    delta: int
    current_hp: int
    max_hp: int
    source: str = "damage"


@register_event
class AbsencePenaltyApplied(BaseRunefobleEvent):
    aggregate_type: str = "CharacterSheet"
    penalty_type: Literal["drunk", "foolishness", "cowardice", "greed", "curse"]
    description: str
    imposed_by: Literal["human_dm", "the_watcher"] = "the_watcher"


PlayerAbsenteePenalized = AbsencePenaltyApplied


@register_event
class AbsencePenaltyCleared(BaseRunefobleEvent):
    aggregate_type: str = "CharacterSheet"
    penalty_type: str


@register_event
class ItemAddedToInventory(BaseRunefobleEvent):
    aggregate_type: str = "CharacterSheet"
    item_id: str
    name: str
    quantity: int = 1
    weight_lbs: float = 0.0


@register_event
class ItemRemovedFromInventory(BaseRunefobleEvent):
    aggregate_type: str = "CharacterSheet"
    item_id: str
    quantity: int = 1


@register_event
class EquipmentSlotUpdated(BaseRunefobleEvent):
    aggregate_type: str = "CharacterSheet"
    slot: str
    item_name: str | None = None


@register_event
class ConditionApplied(BaseRunefobleEvent):
    aggregate_type: str = "CharacterSheet"
    condition: str
    duration_rounds: int | None = None
    source: str = ""


@register_event
class ConditionRemoved(BaseRunefobleEvent):
    aggregate_type: str = "CharacterSheet"
    condition: str


@register_event("runefoble.events.character.leveled_up")
class CharacterLeveledUp(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "CharacterSheet"
    event_type: str = "runefoble.events.character.leveled_up"
    session_id: str = ""
    character_id: str
    new_level: int
    max_hp_increase: int
    spell_slots: dict[int, int] = Field(default_factory=dict)


@register_event("runefoble.events.character.spell_prepared")
class SpellPrepared(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "CharacterSheet"
    event_type: str = "runefoble.events.character.spell_prepared"
    session_id: str = ""
    character_id: str
    spell_name: str
    spell_level: int


@register_event("runefoble.events.character.spell_slot_expended")
class SpellSlotExpended(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "CharacterSheet"
    event_type: str = "runefoble.events.character.spell_slot_expended"
    session_id: str = ""
    character_id: str
    spell_name: str
    slot_level_used: int
    remaining_slots: int


@register_event("runefoble.events.character.stand_in_policy_updated")
class StandInPolicyUpdated(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "CharacterSheet"
    event_type: str = "runefoble.events.character.stand_in_policy_updated"
    character_id: UUID | str
    guardrails: dict[str, Any] = Field(default_factory=dict)


@register_event("runefoble.events.character.stand_in_stabilized")
class StandInStabilized(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "CharacterSheet"
    event_type: str = "runefoble.events.character.stand_in_stabilized"
    character_id: UUID | str
    current_hp: int = 0
    condition: str = "unconscious_stabilized"


# Legacy backward-compatible alias
SessionPenaltyEvent = AbsencePenaltyApplied
CharacterConditionApplied = ConditionApplied


@register_event("runefoble.events.character.critical_hit_scored")
class CriticalHitScored(BaseRunefobleEvent):
    """Emitted when a character scores a critical hit or natural 20."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "CharacterSheet"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.character.critical_hit_scored"
    session_id: str
    character_id: str
    character_name: str = ""
    target_id: str | None = None
    target_name: str | None = None
    roll_total: int = 20


CriticalHitRolled = CriticalHitScored


@register_event("runefoble.events.character.death_save_started")
class DeathSaveStarted(BaseRunefobleEvent):
    """Emitted when a character drops to 0 HP and begins death saves."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "CharacterSheet"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.character.death_save_started"
    session_id: str
    character_id: str
    character_name: str = ""
    current_hp: int = 0


@register_event("runefoble.events.character.damaged")
class CharacterDamaged(BaseRunefobleEvent):
    """Emitted when a character takes damage, reducing hit points."""

    suppress_event_type_warning: ClassVar[bool] = True
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

    suppress_event_type_warning: ClassVar[bool] = True
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

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "CharacterSheet"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.character.portrait_updated"
    character_id: UUID | str
    active_portrait_url: str
    variant_id: str | None = None


# Backward-compatible alias
PortraitAssigned = CharacterPortraitUpdated


@register_event("runefoble.events.character.assigned_to_campaign")
@register_event("character.assigned_to_campaign", schema_version=1)
class CharacterAssignedToCampaign(BaseRunefobleEvent):
    """Emitted when a character is assigned to or unassigned from a campaign."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "CharacterSheet"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "character.assigned_to_campaign"
    character_id: str = ""
    campaign_id: str | None = None
    assigned_by: str = ""
