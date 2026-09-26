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
    CharacterLeveledUp,
    ConditionApplied,
    ConditionRemoved,
    EquipmentSlotUpdated,
    ItemAddedToInventory,
    ItemRemovedFromInventory,
    SpellPrepared,
    SpellSlotExpended,
)

SPELL_SLOTS_TABLE: dict[int, dict[int, int]] = {
    1: {1: 2},
    2: {1: 3},
    3: {1: 4, 2: 2},
    4: {1: 4, 2: 3},
    5: {1: 4, 2: 3, 3: 2},
    6: {1: 4, 2: 3, 3: 3},
    7: {1: 4, 2: 3, 3: 3, 4: 1},
    8: {1: 4, 2: 3, 3: 3, 4: 2},
    9: {1: 4, 2: 3, 3: 3, 4: 3, 5: 1},
    10: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2},
}

CLASS_HIT_DIE: dict[str, int] = {
    "barbarian": 12,
    "fighter": 10,
    "paladin": 10,
    "ranger": 10,
    "cleric": 8,
    "druid": 8,
    "monk": 8,
    "rogue": 8,
    "bard": 8,
    "warlock": 8,
    "wizard": 6,
    "sorcerer": 6,
}

KNOWN_SPELL_LEVELS: dict[str, int] = {
    "magic missile": 1,
    "shield": 1,
    "mage armor": 1,
    "cure wounds": 1,
    "guiding bolt": 1,
    "misty step": 2,
    "scorching ray": 2,
    "invisibility": 2,
    "hold person": 2,
    "mirror image": 2,
    "fireball": 3,
    "fly": 3,
    "counterspell": 3,
    "lightning bolt": 3,
    "haste": 3,
}


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

    def level_up(
        self,
        target_level: int | None = None,
        hp_increase: int | None = None,
        session_id: str = "",
    ) -> None:
        """Advance character level, increase hit points, and scale spell slots."""
        new_level = target_level if target_level is not None else self.state.level + 1
        if hp_increase is None:
            hp_increase = CLASS_HIT_DIE.get(self.state.character_class.lower(), 8)
        spell_slots = dict(SPELL_SLOTS_TABLE.get(new_level, self.state.spell_slots))
        self.create_event(
            CharacterLeveledUp,
            session_id=session_id,
            character_id=str(self.aggregate_id),
            new_level=new_level,
            max_hp_increase=hp_increase,
            spell_slots=spell_slots,
        )

    def prepare_spell(
        self, spell_name: str, spell_level: int | None = None, session_id: str = ""
    ) -> None:
        """Prepare a spell in the character's active spellbook."""
        if spell_level is None or spell_level <= 0:
            spell_level = KNOWN_SPELL_LEVELS.get(spell_name.lower(), 1)
        self.create_event(
            SpellPrepared,
            session_id=session_id,
            character_id=str(self.aggregate_id),
            spell_name=spell_name,
            spell_level=spell_level,
        )

    def cast_spell(
        self, spell_name: str, slot_level: int | None = None, session_id: str = ""
    ) -> None:
        """Cast a prepared spell, expending an appropriate level spell slot."""
        if slot_level is None or slot_level <= 0:
            slot_level = KNOWN_SPELL_LEVELS.get(spell_name.lower(), 1)
        available_slots = self.state.spell_slots.get(slot_level, 0)
        if available_slots <= 0:
            raise ValueError(
                f"INSUFFICIENT_SPELL_SLOTS: Character '{self.aggregate_id}' has 0 level {slot_level} spell slots remaining to cast '{spell_name}'"
            )
        self.create_event(
            SpellSlotExpended,
            session_id=session_id,
            character_id=str(self.aggregate_id),
            spell_name=spell_name,
            slot_level_used=slot_level,
            remaining_slots=available_slots - 1,
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
            level=1,
            xp=0,
            spellbook=[],
            prepared_spells=[],
            spell_slots=dict(SPELL_SLOTS_TABLE.get(1, {1: 2})),
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

    @handles(CharacterLeveledUp)
    def _on_leveled_up(self, event: CharacterLeveledUp) -> None:
        self._state = self.state.model_copy(
            update={
                "level": event.new_level,
                "max_hp": self.state.max_hp + event.max_hp_increase,
                "current_hp": self.state.current_hp + event.max_hp_increase,
                "spell_slots": event.spell_slots,
            }
        )

    @handles(SpellPrepared)
    def _on_spell_prepared(self, event: SpellPrepared) -> None:
        prep = list(self.state.prepared_spells)
        if event.spell_name not in prep:
            prep.append(event.spell_name)
        book = list(self.state.spellbook)
        if event.spell_name not in book:
            book.append(event.spell_name)
        self._state = self.state.model_copy(update={"prepared_spells": prep, "spellbook": book})

    @handles(SpellSlotExpended)
    def _on_spell_slot_expended(self, event: SpellSlotExpended) -> None:
        slots = dict(self.state.spell_slots)
        slots[event.slot_level_used] = event.remaining_slots
        self._state = self.state.model_copy(update={"spell_slots": slots})
