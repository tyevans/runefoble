"""Pydantic request schemas for the Character Sheet microservice."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CreateCharacterRequest(BaseModel):
    name: str
    character_class: str
    max_hp: int = 30
    player_id: str | None = None
    personality_traits: list[str] = ["brave", "curious"]
    campaign_id: str | None = None
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


class AssignCampaignRequest(BaseModel):
    campaign_id: str | None = None
    assigned_by: str | None = None


class HealthChangeRequest(BaseModel):
    delta: int
    source: str = "damage"
    is_stand_in: bool | None = None


class UpdateGuardrailsRequest(BaseModel):
    preserve_spell_slots: dict[int, int] = Field(default_factory=dict)
    protect_allies: list[str] = Field(default_factory=list)
    protect_ally_hp_threshold: float = 0.3
    risk_threshold: Literal["cautious", "balanced", "reckless"] = "cautious"
    avoid_melee: bool = True
    permadeath_safeguard: bool = True
    custom_priorities: list[str] = Field(default_factory=list)


class PenaltyRequest(BaseModel):
    penalty_type: Literal["drunk", "foolishness", "cowardice", "greed", "curse"]
    description: str
    imposed_by: Literal["human_dm", "the_watcher"] = "the_watcher"


class AddInventoryItemRequest(BaseModel):
    item_id: str
    name: str
    quantity: int = 1
    weight_lbs: float = 0.0


class RemoveInventoryItemRequest(BaseModel):
    quantity: int = 1


class EquipItemRequest(BaseModel):
    slot: str
    item_name: str | None = None


class ApplyConditionRequest(BaseModel):
    condition: str
    duration_rounds: int | None = None
    source: str = ""


class LevelUpRequest(BaseModel):
    target_level: int | None = None
    hp_increase: int | None = None
    session_id: str = ""


class PrepareSpellRequest(BaseModel):
    spell_name: str
    spell_level: int | None = None
    session_id: str = ""


class CastSpellRequest(BaseModel):
    spell_name: str
    slot_level: int | None = None
    session_id: str = ""


class AddWardrobeVariantRequest(BaseModel):
    variant_id: str | None = None
    variant_name: str
    attire_type: str = "base"
    image_url: str
    prompt: str = ""
    set_active: bool = False


class SetActivePortraitRequest(BaseModel):
    variant_id: str | None = None
    image_url: str | None = None


class PortraitResponse(BaseModel):
    character_id: str
    active_portrait_url: str
    base_portrait_url: str
    active_variant_id: str | None = None
    condition_badges: list[str] = Field(default_factory=list)
    svg_overlay: str = ""
    current_hp: int
    max_hp: int
