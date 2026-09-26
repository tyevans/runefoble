"""Pydantic state schemas and API request models for character sheets."""

from typing import Literal
from uuid import UUID

from character_sheet.rules import SPELL_SLOTS_TABLE
from pydantic import BaseModel, Field


class InventoryItem(BaseModel):
    item_id: str
    name: str
    quantity: int = 1
    weight_lbs: float = 0.0


class ConditionState(BaseModel):
    condition: str
    duration_rounds: int | None = None
    source: str = ""


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
    ) -> "CharacterState":
        return cls(
            character_id=character_id,
            name=name,
            character_class=character_class,
            max_hp=max_hp,
            current_hp=current_hp,
            player_id=player_id,
            personality_traits=personality_traits or [],
            spell_slots=dict(SPELL_SLOTS_TABLE.get(1, {1: 2})),
        )

    def with_health(self, current_hp: int) -> "CharacterState":
        return self.model_copy(update={"current_hp": current_hp})

    def with_penalty(self, penalty_type: str, description: str) -> "CharacterState":
        pens = dict(self.penalties)
        pens[penalty_type.lower()] = description
        return self.model_copy(update={"penalties": pens})

    def without_penalty(self, penalty_type: str) -> "CharacterState":
        pens = dict(self.penalties)
        pens.pop(penalty_type.lower(), None)
        return self.model_copy(update={"penalties": pens})

    def with_inventory_item(
        self, item_id: str, name: str, quantity: int, weight_lbs: float
    ) -> "CharacterState":
        inv = dict(self.inventory)
        iid = str(item_id)
        if iid in inv:
            inv[iid] = inv[iid].model_copy(update={"quantity": inv[iid].quantity + quantity})
        else:
            inv[iid] = InventoryItem(
                item_id=iid, name=name, quantity=quantity, weight_lbs=weight_lbs
            )
        return self.model_copy(update={"inventory": inv})

    def without_inventory_item(self, item_id: str, quantity: int) -> "CharacterState":
        inv = dict(self.inventory)
        iid = str(item_id)
        if iid in inv:
            if inv[iid].quantity <= quantity:
                inv.pop(iid, None)
            else:
                inv[iid] = inv[iid].model_copy(update={"quantity": inv[iid].quantity - quantity})
        return self.model_copy(update={"inventory": inv})

    def with_equipment_slot(self, slot: str, item_name: str | None) -> "CharacterState":
        eq = dict(self.equipment)
        if item_name is None:
            eq.pop(slot, None)
        else:
            eq[slot] = item_name
        return self.model_copy(update={"equipment": eq})

    def with_condition(
        self, condition: str, duration_rounds: int | None, source: str
    ) -> "CharacterState":
        conds = dict(self.conditions)
        conds[condition] = ConditionState(
            condition=condition, duration_rounds=duration_rounds, source=source
        )
        return self.model_copy(update={"conditions": conds})

    def without_condition(self, condition: str) -> "CharacterState":
        conds = dict(self.conditions)
        conds.pop(condition, None)
        return self.model_copy(update={"conditions": conds})

    def with_level_up(
        self, new_level: int, max_hp_increase: int, spell_slots: dict[int, int]
    ) -> "CharacterState":
        return self.model_copy(
            update={
                "level": new_level,
                "max_hp": self.max_hp + max_hp_increase,
                "current_hp": self.current_hp + max_hp_increase,
                "spell_slots": spell_slots,
            }
        )

    def with_prepared_spell(self, spell_name: str) -> "CharacterState":
        prep = list(self.prepared_spells)
        if spell_name not in prep:
            prep.append(spell_name)
        book = list(self.spellbook)
        if spell_name not in book:
            book.append(spell_name)
        return self.model_copy(update={"prepared_spells": prep, "spellbook": book})

    def with_expended_spell_slot(self, slot_level: int, remaining: int) -> "CharacterState":
        slots = dict(self.spell_slots)
        slots[slot_level] = remaining
        return self.model_copy(update={"spell_slots": slots})


# Alias for explicit domain nomenclature
CharacterSheetState = CharacterState


class CreateCharacterRequest(BaseModel):
    name: str
    character_class: str
    max_hp: int = 30
    player_id: str | None = None
    personality_traits: list[str] = ["brave", "curious"]


class HealthChangeRequest(BaseModel):
    delta: int
    source: str = "damage"


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
