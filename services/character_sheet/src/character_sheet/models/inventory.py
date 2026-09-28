"""Inventory, equipment slots, and encumbrance models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class InventoryItem(BaseModel):
    item_id: str
    name: str
    quantity: int = 1
    weight_lbs: float = 0.0
    slot: str | None = None


class EquipmentSlot(BaseModel):
    slot: str
    item_name: str | None = None
    item_id: str | None = None


class Encumbrance(BaseModel):
    current_weight_lbs: float = 0.0
    capacity_lbs: float = 150.0
    tier: Literal["light", "medium", "heavy", "overburdened"] = "light"

    @classmethod
    def calculate(
        cls,
        items: list[InventoryItem] | dict[str, InventoryItem],
        strength: int = 10,
    ) -> Encumbrance:
        item_list = items.values() if isinstance(items, dict) else items
        total_weight = sum(item.quantity * item.weight_lbs for item in item_list)
        capacity = max(1.0, float(strength * 15))
        ratio = total_weight / capacity
        if ratio <= 0.33:
            tier = "light"
        elif ratio <= 0.66:
            tier = "medium"
        elif ratio <= 1.0:
            tier = "heavy"
        else:
            tier = "overburdened"
        return cls(
            current_weight_lbs=round(total_weight, 2),
            capacity_lbs=round(capacity, 2),
            tier=tier,
        )


class InventoryTransitionsMixin:
    """Transition methods for character inventory items and equipment slots."""

    def with_inventory_item(
        self: Any, item_id: str, name: str, quantity: int, weight_lbs: float
    ) -> Any:
        inv = dict(self.inventory)
        iid = str(item_id)
        if iid in inv:
            inv[iid] = inv[iid].model_copy(update={"quantity": inv[iid].quantity + quantity})
        else:
            inv[iid] = InventoryItem(
                item_id=iid, name=name, quantity=quantity, weight_lbs=weight_lbs
            )
        return self.model_copy(update={"inventory": inv})

    def without_inventory_item(self: Any, item_id: str, quantity: int) -> Any:
        inv = dict(self.inventory)
        iid = str(item_id)
        if iid in inv:
            if inv[iid].quantity <= quantity:
                inv.pop(iid, None)
            else:
                inv[iid] = inv[iid].model_copy(update={"quantity": inv[iid].quantity - quantity})
        return self.model_copy(update={"inventory": inv})

    def with_equipment_slot(self: Any, slot: str, item_name: str | None) -> Any:
        eq = dict(self.equipment)
        if item_name is None:
            eq.pop(slot, None)
        else:
            eq[slot] = item_name
        return self.model_copy(update={"equipment": eq})
