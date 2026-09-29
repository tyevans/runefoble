"""Pydantic schemas and serialization models for character management."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CreateCharacterRequest(BaseModel):
    id: str | None = None
    name: str = Field(..., min_length=1, max_length=100)
    character_class: str = Field(default="Fighter", alias="characterClass")
    subclass: str | None = None
    level: int = Field(default=1, ge=1, le=20)
    current_hp: int | None = Field(default=None, alias="currentHp")
    max_hp: int = Field(default=10, ge=1, alias="maxHp")
    armor_class: int = Field(default=10, ge=1, alias="armorClass")
    speed: int = Field(default=30, ge=0)
    campaign_id: str | None = Field(default=None, alias="campaignId")
    portrait_url: str | None = Field(default=None, alias="portraitUrl")
    is_stand_in_active: bool = Field(default=False, alias="isAiStandIn")

    model_config = ConfigDict(populate_by_name=True)


class AssignCampaignRequest(BaseModel):
    campaign_id: str | None = Field(default=None, alias="campaignId")
    campaign_title: str | None = Field(default=None, alias="campaignTitle")

    model_config = ConfigDict(populate_by_name=True)


class CharacterResponse(BaseModel):
    id: str
    name: str
    character_class: str
    subclass: str | None = None
    level: int
    current_hp: int
    max_hp: int
    armor_class: int
    speed: int = 30
    campaign_id: str | None = None
    campaign_title: str | None = None
    owner_id: str = ""
    portrait_url: str | None = None
    equipment: dict[str, Any] = Field(default_factory=dict)
    inventory: dict[str, Any] = Field(default_factory=dict)
    conditions: dict[str, Any] = Field(default_factory=dict)
    penalties: dict[str, str] = Field(default_factory=dict)
    spell_slots: dict[int, int] = Field(default_factory=lambda: {1: 4, 2: 2})
    max_spell_slots: dict[int, int] = Field(default_factory=lambda: {1: 4, 2: 2})
    prepared_spells: list[str] = Field(default_factory=list)
    spellbook: list[str] = Field(default_factory=list)
    stand_in_guardrails: dict[str, Any] = Field(default_factory=dict)
    is_stand_in_active: bool = False
    is_stabilized: bool = False

    # CamelCase mirrors for frontend compatibility
    characterClass: str | None = None
    currentHp: int | None = None
    maxHp: int | None = None
    armorClass: int | None = None
    campaignId: str | None = None
    campaignTitle: str | None = None
    ownerId: str | None = None
    portraitUrl: str | None = None
    spellSlots: dict[int, int] | None = None
    maxSpellSlots: dict[int, int] | None = None
    preparedSpells: list[str] | None = None
    standInGuardrails: dict[str, Any] | None = None
    isAiStandIn: bool | None = None
    isStabilized: bool | None = None

    model_config = ConfigDict(populate_by_name=True)

    def model_post_init(self, __context: Any) -> None:
        if self.characterClass is None:
            self.characterClass = self.character_class
        if self.currentHp is None:
            self.currentHp = self.current_hp
        if self.maxHp is None:
            self.maxHp = self.max_hp
        if self.armorClass is None:
            self.armorClass = self.armor_class
        if self.campaignId is None:
            self.campaignId = self.campaign_id
        if self.campaignTitle is None:
            self.campaignTitle = self.campaign_title
        if self.ownerId is None:
            self.ownerId = self.owner_id
        if self.portraitUrl is None:
            self.portraitUrl = self.portrait_url
        if self.spellSlots is None:
            self.spellSlots = dict(self.spell_slots)
        if self.maxSpellSlots is None:
            self.maxSpellSlots = dict(self.max_spell_slots)
        if self.preparedSpells is None:
            self.preparedSpells = list(self.prepared_spells)
        if self.standInGuardrails is None:
            self.standInGuardrails = dict(self.stand_in_guardrails)
        if self.isAiStandIn is None:
            self.isAiStandIn = self.is_stand_in_active
        if self.isStabilized is None:
            self.isStabilized = self.is_stabilized


class StandInGuardrailsRequest(BaseModel):
    preserve_spell_slots: dict[int, int] = Field(default_factory=dict, alias="preserveSpellSlots")
    protect_allies: list[str] = Field(default_factory=list, alias="protectAllies")
    protect_ally_hp_threshold: float = Field(default=0.3, alias="protectAllyHpThreshold")
    risk_threshold: str = Field(default="cautious", alias="riskThreshold")
    avoid_melee: bool = Field(default=True, alias="avoidMelee")
    permadeath_safeguard: bool = Field(default=True, alias="permadeathSafeguard")
    custom_priorities: list[str] = Field(default_factory=list, alias="customPriorities")

    model_config = ConfigDict(populate_by_name=True)


class HealthChangeRequest(BaseModel):
    delta: int
    source: str = "damage"
    is_stand_in: bool | None = Field(default=None, alias="isStandIn")

    model_config = ConfigDict(populate_by_name=True)


class EquipItemRequest(BaseModel):
    slot: str
    item_name: str | None = Field(default=None, alias="itemName")

    model_config = ConfigDict(populate_by_name=True)


class AddInventoryItemRequest(BaseModel):
    item_id: str | None = Field(default=None, alias="itemId")
    name: str
    quantity: int = 1
    weight_lbs: float = Field(default=0.0, alias="weightLbs")

    model_config = ConfigDict(populate_by_name=True)


class RemoveInventoryItemRequest(BaseModel):
    quantity: int = 1


class ApplyConditionRequest(BaseModel):
    condition: str
    duration_rounds: int | None = Field(default=None, alias="durationRounds")
    source: str = ""

    model_config = ConfigDict(populate_by_name=True)


class CastSpellRequest(BaseModel):
    spell_name: str = Field(..., alias="spellName")
    slot_level: int | None = Field(default=1, alias="slotLevel")
    session_id: str = Field(default="", alias="sessionId")

    model_config = ConfigDict(populate_by_name=True)


class PrepareSpellRequest(BaseModel):
    spell_name: str = Field(..., alias="spellName")
    spell_level: int | None = Field(default=None, alias="spellLevel")
    is_prepared: bool = Field(default=True, alias="isPrepared")
    prepared: bool | None = None
    session_id: str = Field(default="", alias="sessionId")

    model_config = ConfigDict(populate_by_name=True)


__all__ = [
    "AddInventoryItemRequest",
    "ApplyConditionRequest",
    "AssignCampaignRequest",
    "CastSpellRequest",
    "CharacterResponse",
    "CreateCharacterRequest",
    "EquipItemRequest",
    "HealthChangeRequest",
    "PrepareSpellRequest",
    "RemoveInventoryItemRequest",
    "StandInGuardrailsRequest",
]
