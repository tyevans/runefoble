"""Event-sourced CharacterSheet aggregate using eventsource-py."""

from typing import Any, Literal

from character_sheet.models import (
    CharacterSheetState,
    CharacterState,
    ConditionState,
    InventoryItem,
    StandInGuardrails,
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
    StandInPolicyUpdated,
    StandInStabilized,
)

__all__ = [
    "CLASS_HIT_DIE",
    "KNOWN_SPELL_LEVELS",
    "SPELL_SLOTS_TABLE",
    "CharacterAggregate",
    "CharacterSheetState",
    "CharacterState",
    "ConditionState",
    "InventoryItem",
    "get_hit_die_for_class",
    "get_known_spell_level",
    "get_spell_slots_for_level",
]


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

    def modify_health(
        self, delta: int, source: str = "damage", is_stand_in: bool | None = None
    ) -> None:
        """Apply damage or healing with zero-HP permadeath safeguard for stand-ins."""
        effective_stand_in = (
            is_stand_in if is_stand_in is not None else self.state.is_stand_in_active
        )
        if (
            delta < 0
            and (self.state.current_hp + delta <= 0)
            and effective_stand_in
            and self.state.stand_in_guardrails.permadeath_safeguard
        ):
            self.create_event(
                CharacterHealthChanged,
                delta=delta,
                current_hp=0,
                max_hp=self.state.max_hp,
                source=source,
            )
            self.create_event(
                StandInStabilized,
                character_id=str(self.aggregate_id),
                current_hp=0,
                condition="unconscious_stabilized",
            )
            self.create_event(
                ConditionApplied,
                condition="unconscious_stabilized",
                duration_rounds=None,
                source="permadeath_safeguard",
            )
            return

        new_hp = max(0, min(self.state.max_hp, self.state.current_hp + delta))
        self.create_event(
            CharacterHealthChanged,
            delta=delta,
            current_hp=new_hp,
            max_hp=self.state.max_hp,
            source=source,
        )

    def update_stand_in_guardrails(self, guardrails: StandInGuardrails | dict[str, Any]) -> None:
        """Configure tactical constraints for stand-in AI."""
        if isinstance(guardrails, StandInGuardrails):
            gr_dict = guardrails.model_dump()
        else:
            gr_dict = dict(guardrails)
        self.create_event(
            StandInPolicyUpdated,
            character_id=str(self.aggregate_id),
            guardrails=gr_dict,
        )

    def set_stand_in_active(self, active: bool) -> None:
        """Set whether the character is currently piloted by the stand-in AI."""
        self._state = self.state.with_stand_in_active(active)

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
        self.create_event(AbsencePenaltyCleared, penalty_type=penalty_type.lower())

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
        self.create_event(ItemRemovedFromInventory, item_id=iid, quantity=quantity)

    def equip_item(self, slot: str, item_name: str | None = None) -> None:
        """Equip or unequip an item into a designated equipment slot (e.g. 'main_hand', 'armor')."""
        self.create_event(EquipmentSlotUpdated, slot=slot.lower(), item_name=item_name)

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
        self.create_event(ConditionRemoved, condition=cond)

    def level_up(
        self,
        target_level: int | None = None,
        hp_increase: int | None = None,
        session_id: str = "",
    ) -> None:
        """Advance character level, increase hit points, and scale spell slots."""
        new_level = target_level if target_level is not None else self.state.level + 1
        if hp_increase is None:
            hp_increase = get_hit_die_for_class(self.state.character_class)
        spell_slots = get_spell_slots_for_level(new_level, self.state.spell_slots)
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
            spell_level = get_known_spell_level(spell_name)
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
            slot_level = get_known_spell_level(spell_name)
        available_slots = self.state.spell_slots.get(slot_level, 0)
        if available_slots <= 0:
            raise ValueError(
                f"INSUFFICIENT_SPELL_SLOTS: Character '{self.aggregate_id}' has 0 level {slot_level} spell slots remaining to cast '{spell_name}'"
            )
        if self.state.is_stand_in_active:
            preserve_count = self.state.stand_in_guardrails.preserve_spell_slots.get(slot_level, 0)
            if available_slots <= preserve_count:
                raise ValueError(
                    f"STAND_IN_GUARDRAIL_VIOLATION: Character '{self.aggregate_id}' has {available_slots} level {slot_level} spell slots, but stand-in tactical policy reserves {preserve_count} slot(s)."
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
        self._state = CharacterState.initial(
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
        self._state = self.state.with_health(event.current_hp)

    @handles(AbsencePenaltyApplied)
    def _on_penalty_applied(self, event: AbsencePenaltyApplied) -> None:
        self._state = self.state.with_penalty(event.penalty_type, event.description)

    @handles(AbsencePenaltyCleared)
    def _on_penalty_cleared(self, event: AbsencePenaltyCleared) -> None:
        self._state = self.state.without_penalty(event.penalty_type)

    @handles(ItemAddedToInventory)
    def _on_item_added(self, event: ItemAddedToInventory) -> None:
        self._state = self.state.with_inventory_item(
            item_id=event.item_id,
            name=event.name,
            quantity=event.quantity,
            weight_lbs=event.weight_lbs,
        )

    @handles(ItemRemovedFromInventory)
    def _on_item_removed(self, event: ItemRemovedFromInventory) -> None:
        self._state = self.state.without_inventory_item(
            item_id=event.item_id, quantity=event.quantity
        )

    @handles(EquipmentSlotUpdated)
    def _on_equipment_updated(self, event: EquipmentSlotUpdated) -> None:
        self._state = self.state.with_equipment_slot(event.slot, event.item_name)

    @handles(ConditionApplied)
    def _on_condition_applied(self, event: ConditionApplied) -> None:
        self._state = self.state.with_condition(
            event.condition, event.duration_rounds, event.source
        )

    @handles(ConditionRemoved)
    def _on_condition_removed(self, event: ConditionRemoved) -> None:
        self._state = self.state.without_condition(event.condition)

    @handles(CharacterLeveledUp)
    def _on_leveled_up(self, event: CharacterLeveledUp) -> None:
        self._state = self.state.with_level_up(
            new_level=event.new_level,
            max_hp_increase=event.max_hp_increase,
            spell_slots=event.spell_slots,
        )

    @handles(SpellPrepared)
    def _on_spell_prepared(self, event: SpellPrepared) -> None:
        self._state = self.state.with_prepared_spell(event.spell_name)

    @handles(SpellSlotExpended)
    def _on_spell_slot_expended(self, event: SpellSlotExpended) -> None:
        self._state = self.state.with_expended_spell_slot(
            slot_level=event.slot_level_used, remaining=event.remaining_slots
        )

    @handles(StandInPolicyUpdated)
    def _on_guardrails_updated(self, event: StandInPolicyUpdated) -> None:
        self._state = self.state.with_stand_in_guardrails(event.guardrails)

    @handles(StandInStabilized)
    def _on_stand_in_stabilized(self, event: StandInStabilized) -> None:
        self._state = self.state.with_stabilized()
