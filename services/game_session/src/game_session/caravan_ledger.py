"""Caravan trade and resource ledger aggregate for West Marches frontier economy.

Part of TASK-0127 / PRD-0007 / US-0058 / ADR-0006 / ADR-0011.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from pydantic import BaseModel, Field
from runefoble_events.west_marches import (
    CaravanDispatched,
    CaravanTradeCompleted,
    RegionalMerchantStockUpdated,
)


def _to_uuid(val: Any) -> UUID | None:
    if not val:
        return None
    try:
        return UUID(str(val))
    except Exception:
        return None


class CaravanLedgerState(BaseModel):
    """Event-sourced state for cross-campaign trade routes, caravans, and regional merchant stock."""

    shared_world_id: str = ""
    caravans: dict[str, dict[str, Any]] = Field(default_factory=dict)
    outpost_stocks: dict[str, dict[str, Any]] = Field(default_factory=dict)


class CaravanLedgerAggregate(DeclarativeAggregate[CaravanLedgerState]):
    """Event-sourced aggregate managing frontier caravan routes and merchant inventories."""

    aggregate_type = "CaravanLedger"
    requires_creation_event = False

    def __init__(self, aggregate_id: Any = None, **kwargs: Any) -> None:
        super().__init__(aggregate_id=aggregate_id, **kwargs)
        if self._state is None:
            self._state = CaravanLedgerState(shared_world_id=str(aggregate_id or ""))

    @handles(CaravanDispatched)
    def handle_dispatched(self, event: CaravanDispatched) -> None:
        self.state.caravans[event.caravan_id] = {
            "caravan_id": event.caravan_id,
            "origin_outpost": event.origin_outpost,
            "destination_outpost": event.destination_outpost,
            "cargo": dict(event.cargo),
            "dispatched_by_campaign_id": str(event.dispatched_by_campaign_id),
            "transit_turns": event.transit_turns,
            "status": event.status,
            "dispatched_at": datetime.now(UTC).isoformat(),
        }

    @handles(CaravanTradeCompleted)
    def handle_trade_completed(self, event: CaravanTradeCompleted) -> None:
        if event.caravan_id in self.state.caravans:
            self.state.caravans[event.caravan_id]["status"] = "completed"
            self.state.caravans[event.caravan_id]["completed_at"] = event.completed_at

        dest = event.destination_outpost.lower()
        if dest not in self.state.outpost_stocks:
            self.state.outpost_stocks[dest] = {
                "inventory": {},
                "workshop_reagents": {},
                "last_delivery": None,
            }
        stock = self.state.outpost_stocks[dest]
        stock["last_delivery"] = event.caravan_id

        for item, qty in event.cargo_delivered.items():
            stock["workshop_reagents"][item] = stock["workshop_reagents"].get(item, 0) + qty

        for key, val in event.unlocked_stock.items():
            stock["inventory"][key] = val

    @handles(RegionalMerchantStockUpdated)
    def handle_stock_updated(self, event: RegionalMerchantStockUpdated) -> None:
        dest = event.outpost_name.lower()
        if dest not in self.state.outpost_stocks:
            self.state.outpost_stocks[dest] = {"inventory": {}, "workshop_reagents": {}}
        self.state.outpost_stocks[dest]["inventory"].update(event.inventory_updates)

    def dispatch_caravan(
        self,
        origin_outpost: str,
        destination_outpost: str,
        cargo: dict[str, int],
        dispatched_by_campaign_id: UUID | str,
        transit_turns: int = 1,
        caravan_id: str | None = None,
    ) -> str:
        cid = caravan_id or f"caravan_{uuid4().hex[:8]}"
        wid = _to_uuid(self.state.shared_world_id or self.aggregate_id)
        camp_id = _to_uuid(dispatched_by_campaign_id) or str(dispatched_by_campaign_id)
        self.create_event(
            CaravanDispatched,
            shared_world_id=wid,
            caravan_id=cid,
            origin_outpost=origin_outpost,
            destination_outpost=destination_outpost,
            cargo=cargo,
            dispatched_by_campaign_id=camp_id,
            transit_turns=transit_turns,
            status="in_transit",
        )
        return cid

    def complete_caravan_trade(
        self,
        caravan_id: str,
        unlocked_stock: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if caravan_id not in self.state.caravans:
            raise ValueError(f"Caravan '{caravan_id}' not found")
        caravan = self.state.caravans[caravan_id]
        if caravan["status"] == "completed":
            return caravan

        wid = _to_uuid(self.state.shared_world_id or self.aggregate_id)
        now_iso = datetime.now(UTC).isoformat()
        delivered_cargo = dict(caravan["cargo"])

        default_unlocked = {}
        for reagent, qty in delivered_cargo.items():
            default_unlocked[f"refined_{reagent}"] = {
                "name": f"Refined {reagent.replace('_', ' ').title()}",
                "price_gold": 25,
                "quantity": qty * 2,
                "rarity": "rare",
            }
        effective_unlocked = unlocked_stock if unlocked_stock is not None else default_unlocked

        self.create_event(
            CaravanTradeCompleted,
            shared_world_id=wid,
            caravan_id=caravan_id,
            origin_outpost=caravan["origin_outpost"],
            destination_outpost=caravan["destination_outpost"],
            cargo_delivered=delivered_cargo,
            unlocked_stock=effective_unlocked,
            completed_at=now_iso,
        )
        return self.state.caravans[caravan_id]


__all__ = [
    "CaravanLedgerAggregate",
    "CaravanLedgerState",
]
