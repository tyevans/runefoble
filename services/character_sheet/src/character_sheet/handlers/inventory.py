"""Inventory and equipment mutation handlers and event reducers."""

from typing import Any

from character_sheet.models import CharacterState
from eventsource.domain.decorators import handles
from runefoble_events.events import (
    EquipmentSlotUpdated,
    ItemAddedToInventory,
    ItemRemovedFromInventory,
)


class InventoryHandlerMixin:
    """Mixin providing inventory management and equipment slot mutations."""

    _state: CharacterState | None
    state: CharacterState
    create_event: Any
    aggregate_id: Any

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
