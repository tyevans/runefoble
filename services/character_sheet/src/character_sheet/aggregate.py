"""Event-sourced CharacterSheet aggregate using eventsource-py."""

from typing import Literal
from uuid import UUID

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from pydantic import BaseModel, Field
from runefoble_events.events import (
    AbsencePenaltyApplied,
    AbsencePenaltyCleared,
    CharacterCreated,
    CharacterHealthChanged,
    ConditionApplied,
    ConditionRemoved,
    EquipmentSlotUpdated,
    ItemAddedToInventory,
    ItemRemovedFromInventory,
)


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


class CharacterAggregate(DeclarativeAggregate[CharacterState]):
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

    def modify_health(self, delta: int, source: str = "damage") -> None:
        """Apply damage or healing."""
        new_hp = max(0, min(self.state.max_hp, self.state.current_hp + delta))
        self.create_event(
            CharacterHealthChanged,
            delta=delta,
            current_hp=new_hp,
            max_hp=self.state.max_hp,
            source=source,
        )

    def apply_penalty(
        self,
        penalty_type: Literal["drunk", "foolishness", "cowardice", "greed", "curse"],
        description: str,
        imposed_by: Literal["human_dm", "the_watcher"] = "the_watcher",
    ) -> None:
        """Apply a session miss penalty to an absent player's character."""
        self.create_event(
            AbsencePenaltyApplied,
            penalty_type=penalty_type,
            description=description,
            imposed_by=imposed_by,
        )

    def clear_penalty(self, penalty_type: str) -> None:
        """Clear an active penalty once the player returns or redeems themselves."""
        if penalty_type.lower() not in self.state.penalties:
            raise ValueError(f"Penalty '{penalty_type}' is not active on this character")
        self.create_event(
            AbsencePenaltyCleared,
            penalty_type=penalty_type.lower(),
        )

    def add_inventory_item(
        self, item_id: str, name: str, quantity: int = 1, weight_lbs: float = 0.0
    ) -> None:
        """Add an item or currency stack into character inventory."""
        self.create_event(
            ItemAddedToInventory,
            item_id=str(item_id),
            name=name,
            quantity=quantity,
            weight_lbs=weight_lbs,
        )

    def remove_inventory_item(self, item_id: str, quantity: int = 1) -> None:
        """Remove or consume an item from inventory."""
        iid = str(item_id)
        if iid not in self.state.inventory:
            raise ValueError(f"Item '{item_id}' not found in inventory")
        self.create_event(
            ItemRemovedFromInventory,
            item_id=iid,
            quantity=quantity,
        )

    def equip_item(self, slot: str, item_name: str | None = None) -> None:
        """Equip or unequip an item into a designated equipment slot (e.g. 'main_hand', 'armor')."""
        self.create_event(
            EquipmentSlotUpdated,
            slot=slot.lower(),
            item_name=item_name,
        )

    def apply_condition(
        self, condition: str, duration_rounds: int | None = None, source: str = ""
    ) -> None:
        """Inflict an active gameplay condition (e.g. 'blinded', 'prone', 'poisoned')."""
        self.create_event(
            ConditionApplied,
            condition=condition.lower(),
            duration_rounds=duration_rounds,
            source=source,
        )

    def remove_condition(self, condition: str) -> None:
        """Remove a status condition from the character."""
        cond = condition.lower()
        if cond not in self.state.conditions:
            raise ValueError(f"Condition '{condition}' is not active on this character")
        self.create_event(
            ConditionRemoved,
            condition=cond,
        )

    # -----------------------------------------------------------------------
    # Event Handlers (@handles)
    # -----------------------------------------------------------------------

    @handles(CharacterCreated)
    def _on_created(self, event: CharacterCreated) -> None:
        self._state = CharacterState(
            character_id=event.aggregate_id,
            name=event.name,
            character_class=event.character_class,
            max_hp=event.max_hp,
            current_hp=event.current_hp,
            player_id=event.player_id,
            personality_traits=event.personality_traits,
        )

    @handles(CharacterHealthChanged)
    def _on_health_changed(self, event: CharacterHealthChanged) -> None:
        self._state = self.state.model_copy(update={"current_hp": event.current_hp})

    @handles(AbsencePenaltyApplied)
    def _on_penalty_applied(self, event: AbsencePenaltyApplied) -> None:
        pens = dict(self.state.penalties)
        pens[event.penalty_type.lower()] = event.description
        self._state = self.state.model_copy(update={"penalties": pens})

    @handles(AbsencePenaltyCleared)
    def _on_penalty_cleared(self, event: AbsencePenaltyCleared) -> None:
        pens = dict(self.state.penalties)
        pens.pop(event.penalty_type.lower(), None)
        self._state = self.state.model_copy(update={"penalties": pens})

    @handles(ItemAddedToInventory)
    def _on_item_added(self, event: ItemAddedToInventory) -> None:
        inv = dict(self.state.inventory)
        iid = str(event.item_id)
        if iid in inv:
            existing = inv[iid]
            inv[iid] = existing.model_copy(update={"quantity": existing.quantity + event.quantity})
        else:
            inv[iid] = InventoryItem(
                item_id=iid,
                name=event.name,
                quantity=event.quantity,
                weight_lbs=event.weight_lbs,
            )
        self._state = self.state.model_copy(update={"inventory": inv})

    @handles(ItemRemovedFromInventory)
    def _on_item_removed(self, event: ItemRemovedFromInventory) -> None:
        inv = dict(self.state.inventory)
        iid = str(event.item_id)
        if iid in inv:
            existing = inv[iid]
            if existing.quantity <= event.quantity:
                inv.pop(iid, None)
            else:
                inv[iid] = existing.model_copy(
                    update={"quantity": existing.quantity - event.quantity}
                )
        self._state = self.state.model_copy(update={"inventory": inv})

    @handles(EquipmentSlotUpdated)
    def _on_equipment_updated(self, event: EquipmentSlotUpdated) -> None:
        eq = dict(self.state.equipment)
        if event.item_name is None:
            eq.pop(event.slot, None)
        else:
            eq[event.slot] = event.item_name
        self._state = self.state.model_copy(update={"equipment": eq})

    @handles(ConditionApplied)
    def _on_condition_applied(self, event: ConditionApplied) -> None:
        conds = dict(self.state.conditions)
        conds[event.condition] = ConditionState(
            condition=event.condition,
            duration_rounds=event.duration_rounds,
            source=event.source,
        )
        self._state = self.state.model_copy(update={"conditions": conds})

    @handles(ConditionRemoved)
    def _on_condition_removed(self, event: ConditionRemoved) -> None:
        conds = dict(self.state.conditions)
        conds.pop(event.condition, None)
        self._state = self.state.model_copy(update={"conditions": conds})
