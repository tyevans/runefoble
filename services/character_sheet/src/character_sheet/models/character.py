"""Core character state models, attribute scores, and aggregate state."""

from __future__ import annotations

from uuid import UUID

from character_sheet.models.base import (
    DEFAULT_SCORES,
    AttributeScores,
    StandInGuardrails,
    VitalsTransitionsMixin,
    WardrobeVariant,
)
from character_sheet.models.conditions import ConditionState, ConditionsTransitionsMixin
from character_sheet.models.inventory import InventoryItem, InventoryTransitionsMixin
from character_sheet.models.progression import ProgressionTransitionsMixin
from character_sheet.portrait import compute_condition_badges, resolve_active_portrait_url
from character_sheet.rules import SPELL_SLOTS_TABLE
from pydantic import BaseModel, Field


class CharacterCore(BaseModel):
    character_id: UUID
    name: str
    character_class: str
    max_hp: int
    current_hp: int
    player_id: str | None = None
    personality_traits: list[str] = Field(default_factory=list)
    penalties: dict[str, str] = Field(default_factory=dict)
    inventory: dict[str, InventoryItem] = Field(default_factory=dict)
    equipment: dict[str, str] = Field(default_factory=dict)
    conditions: dict[str, ConditionState] = Field(default_factory=dict)
    level: int = 1
    xp: int = 0
    spellbook: list[str] = Field(default_factory=list)
    prepared_spells: list[str] = Field(default_factory=list)
    spell_slots: dict[int, int] = Field(default_factory=lambda: {1: 2})
    stand_in_guardrails: StandInGuardrails = Field(default_factory=StandInGuardrails)
    is_stand_in_active: bool = False
    is_stabilized: bool = False
    base_portrait_url: str = "/assets/portraits/default.svg"
    active_portrait_url: str = "/assets/portraits/default.svg"
    active_variant_id: str | None = None
    wardrobe_variants: dict[str, WardrobeVariant] = Field(default_factory=dict)
    condition_badges: list[str] = Field(default_factory=list)
    campaign_id: str | None = None
    subclass: str | None = None
    armor_class: int = 10
    speed_ft: int = 30
    ability_scores: dict[str, int] = Field(default_factory=lambda: dict(DEFAULT_SCORES))


class CharacterState(
    InventoryTransitionsMixin,
    ConditionsTransitionsMixin,
    ProgressionTransitionsMixin,
    VitalsTransitionsMixin,
    CharacterCore,
):
    @classmethod
    def initial(
        cls,
        character_id: UUID,
        name: str,
        character_class: str,
        max_hp: int,
        current_hp: int,
        player_id: str | None = None,
        personality_traits: list[str] | None = None,
        campaign_id: str | None = None,
        subclass: str | None = None,
        armor_class: int = 10,
        speed_ft: int = 30,
        ability_scores: dict[str, int] | None = None,
    ) -> CharacterState:
        return cls(
            character_id=character_id,
            name=name,
            character_class=character_class,
            max_hp=max_hp,
            current_hp=current_hp,
            player_id=player_id,
            personality_traits=personality_traits or [],
            campaign_id=campaign_id,
            subclass=subclass,
            armor_class=armor_class,
            speed_ft=speed_ft,
            ability_scores=ability_scores if ability_scores is not None else dict(DEFAULT_SCORES),
            spell_slots=dict(SPELL_SLOTS_TABLE.get(1, {1: 2})),
            active_portrait_url=resolve_active_portrait_url(
                "/assets/portraits/default.svg", current_hp, max_hp, {}
            ),
            condition_badges=compute_condition_badges(current_hp, max_hp, {}),
        )


CharacterSheetState = CharacterState
__all__ = ["AttributeScores", "CharacterCore", "CharacterSheetState", "CharacterState"]
