"""Pydantic state schemas and API request models for character sheets."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from character_sheet.portrait import compute_condition_badges, resolve_active_portrait_url
from character_sheet.rules import SPELL_SLOTS_TABLE
from character_sheet.schemas import (
    AddInventoryItemRequest,
    AddWardrobeVariantRequest,
    ApplyConditionRequest,
    AssignCampaignRequest,
    CastSpellRequest,
    CreateCharacterRequest,
    EquipItemRequest,
    HealthChangeRequest,
    LevelUpRequest,
    PenaltyRequest,
    PortraitResponse,
    PrepareSpellRequest,
    RemoveInventoryItemRequest,
    SetActivePortraitRequest,
    UpdateGuardrailsRequest,
)
from pydantic import BaseModel, Field


class WardrobeVariant(BaseModel):
    variant_id: str
    variant_name: str
    attire_type: str = "base"
    image_url: str
    prompt: str = ""
    created_at: str = ""


class InventoryItem(BaseModel):
    item_id: str
    name: str
    quantity: int = 1
    weight_lbs: float = 0.0


class ConditionState(BaseModel):
    condition: str
    duration_rounds: int | None = None
    source: str = ""


class StandInGuardrails(BaseModel):
    preserve_spell_slots: dict[int, int] = Field(default_factory=dict)
    protect_allies: list[str] = Field(default_factory=list)
    protect_ally_hp_threshold: float = 0.3
    risk_threshold: Literal["cautious", "balanced", "reckless"] = "cautious"
    avoid_melee: bool = True
    permadeath_safeguard: bool = True
    custom_priorities: list[str] = Field(default_factory=list)


class CharacterState(BaseModel):
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
        badges = compute_condition_badges(current_hp, max_hp, {})
        active_url = resolve_active_portrait_url(
            "/assets/portraits/default.svg", current_hp, max_hp, {}
        )
        scores = (
            ability_scores
            if ability_scores is not None
            else {
                "str": 10,
                "dex": 10,
                "con": 10,
                "int": 10,
                "wis": 10,
                "cha": 10,
            }
        )
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
            ability_scores=scores,
            spell_slots=dict(SPELL_SLOTS_TABLE.get(1, {1: 2})),
            base_portrait_url="/assets/portraits/default.svg",
            active_portrait_url=active_url,
            condition_badges=badges,
        )

    def with_campaign(self, campaign_id: str | None) -> CharacterState:
        return self.model_copy(update={"campaign_id": campaign_id})

    def with_core_attributes(
        self,
        *,
        subclass: str | None = None,
        armor_class: int | None = None,
        speed_ft: int | None = None,
        ability_scores: dict[str, int] | None = None,
    ) -> CharacterState:
        updates: dict[str, Any] = {}
        if subclass is not None:
            updates["subclass"] = subclass
        if armor_class is not None:
            updates["armor_class"] = armor_class
        if speed_ft is not None:
            updates["speed_ft"] = speed_ft
        if ability_scores is not None:
            updates["ability_scores"] = ability_scores
        return self.model_copy(update=updates)

    def with_health(self, current_hp: int) -> CharacterState:
        badges = compute_condition_badges(current_hp, self.max_hp, self.conditions)
        active_url = resolve_active_portrait_url(
            self.base_portrait_url, current_hp, self.max_hp, self.conditions
        )
        return self.model_copy(
            update={
                "current_hp": current_hp,
                "condition_badges": badges,
                "active_portrait_url": active_url,
            }
        )

    def with_wardrobe_variant(self, variant: WardrobeVariant) -> CharacterState:
        variants = dict(self.wardrobe_variants)
        variants[variant.variant_id] = variant
        return self.model_copy(update={"wardrobe_variants": variants})

    def with_active_portrait(
        self, variant_id: str | None, custom_url: str | None = None
    ) -> CharacterState:
        new_base = self.base_portrait_url
        if variant_id and variant_id in self.wardrobe_variants:
            new_base = self.wardrobe_variants[variant_id].image_url
        elif custom_url:
            new_base = custom_url

        active_url = resolve_active_portrait_url(
            new_base, self.current_hp, self.max_hp, self.conditions
        )
        return self.model_copy(
            update={
                "active_variant_id": variant_id,
                "base_portrait_url": new_base,
                "active_portrait_url": active_url,
            }
        )

    def with_penalty(self, penalty_type: str, description: str) -> CharacterState:
        pens = dict(self.penalties)
        pens[penalty_type.lower()] = description
        return self.model_copy(update={"penalties": pens})

    def without_penalty(self, penalty_type: str) -> CharacterState:
        pens = dict(self.penalties)
        pens.pop(penalty_type.lower(), None)
        return self.model_copy(update={"penalties": pens})

    def with_inventory_item(
        self, item_id: str, name: str, quantity: int, weight_lbs: float
    ) -> CharacterState:
        inv = dict(self.inventory)
        iid = str(item_id)
        if iid in inv:
            inv[iid] = inv[iid].model_copy(update={"quantity": inv[iid].quantity + quantity})
        else:
            inv[iid] = InventoryItem(
                item_id=iid, name=name, quantity=quantity, weight_lbs=weight_lbs
            )
        return self.model_copy(update={"inventory": inv})

    def without_inventory_item(self, item_id: str, quantity: int) -> CharacterState:
        inv = dict(self.inventory)
        iid = str(item_id)
        if iid in inv:
            if inv[iid].quantity <= quantity:
                inv.pop(iid, None)
            else:
                inv[iid] = inv[iid].model_copy(update={"quantity": inv[iid].quantity - quantity})
        return self.model_copy(update={"inventory": inv})

    def with_equipment_slot(self, slot: str, item_name: str | None) -> CharacterState:
        eq = dict(self.equipment)
        if item_name is None:
            eq.pop(slot, None)
        else:
            eq[slot] = item_name
        return self.model_copy(update={"equipment": eq})

    def with_condition(
        self, condition: str, duration_rounds: int | None, source: str
    ) -> CharacterState:
        conds = dict(self.conditions)
        conds[condition] = ConditionState(
            condition=condition, duration_rounds=duration_rounds, source=source
        )
        badges = compute_condition_badges(self.current_hp, self.max_hp, conds)
        active_url = resolve_active_portrait_url(
            self.base_portrait_url, self.current_hp, self.max_hp, conds
        )
        return self.model_copy(
            update={
                "conditions": conds,
                "condition_badges": badges,
                "active_portrait_url": active_url,
            }
        )

    def without_condition(self, condition: str) -> CharacterState:
        conds = dict(self.conditions)
        conds.pop(condition, None)
        badges = compute_condition_badges(self.current_hp, self.max_hp, conds)
        active_url = resolve_active_portrait_url(
            self.base_portrait_url, self.current_hp, self.max_hp, conds
        )
        return self.model_copy(
            update={
                "conditions": conds,
                "condition_badges": badges,
                "active_portrait_url": active_url,
            }
        )

    def with_level_up(
        self, new_level: int, max_hp_increase: int, spell_slots: dict[int, int]
    ) -> CharacterState:
        return self.model_copy(
            update={
                "level": new_level,
                "max_hp": self.max_hp + max_hp_increase,
                "current_hp": self.current_hp + max_hp_increase,
                "spell_slots": spell_slots,
            }
        )

    def with_prepared_spell(self, spell_name: str) -> CharacterState:
        prep = list(self.prepared_spells)
        if spell_name not in prep:
            prep.append(spell_name)
        book = list(self.spellbook)
        if spell_name not in book:
            book.append(spell_name)
        return self.model_copy(update={"prepared_spells": prep, "spellbook": book})

    def with_expended_spell_slot(self, slot_level: int, remaining: int) -> CharacterState:
        slots = dict(self.spell_slots)
        slots[slot_level] = remaining
        return self.model_copy(update={"spell_slots": slots})

    def with_stand_in_guardrails(
        self, guardrails: StandInGuardrails | dict[str, Any]
    ) -> CharacterState:
        if isinstance(guardrails, dict):
            gr = StandInGuardrails.model_validate(guardrails)
        else:
            gr = guardrails
        return self.model_copy(update={"stand_in_guardrails": gr})

    def with_stand_in_active(self, active: bool) -> CharacterState:
        return self.model_copy(update={"is_stand_in_active": active})

    def with_stabilized(self) -> CharacterState:
        conds = dict(self.conditions)
        conds["unconscious_stabilized"] = ConditionState(
            condition="unconscious_stabilized",
            duration_rounds=None,
            source="permadeath_safeguard",
        )
        badges = compute_condition_badges(0, self.max_hp, conds)
        active_url = resolve_active_portrait_url(self.base_portrait_url, 0, self.max_hp, conds)
        return self.model_copy(
            update={
                "current_hp": 0,
                "is_stabilized": True,
                "conditions": conds,
                "condition_badges": badges,
                "active_portrait_url": active_url,
            }
        )


# Alias for explicit domain nomenclature
CharacterSheetState = CharacterState


__all__ = [
    "AddInventoryItemRequest",
    "AddWardrobeVariantRequest",
    "ApplyConditionRequest",
    "AssignCampaignRequest",
    "CastSpellRequest",
    "CharacterSheetState",
    "CharacterState",
    "ConditionState",
    "CreateCharacterRequest",
    "EquipItemRequest",
    "HealthChangeRequest",
    "InventoryItem",
    "LevelUpRequest",
    "PenaltyRequest",
    "PortraitResponse",
    "PrepareSpellRequest",
    "RemoveInventoryItemRequest",
    "SetActivePortraitRequest",
    "StandInGuardrails",
    "UpdateGuardrailsRequest",
    "WardrobeVariant",
]
