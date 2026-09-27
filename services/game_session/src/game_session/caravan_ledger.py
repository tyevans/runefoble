"""Caravan trade and resource ledger aggregate for West Marches frontier economy.

Part of TASK-0127 / TASK-0129 / PRD-0007 / US-0058 / ADR-0006 / ADR-0011.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from pydantic import BaseModel, Field
from runefoble_events.west_marches import (
    CaravanAmbushed,
    CaravanContractAccepted,
    CaravanContractPosted,
    CaravanDispatched,
    CaravanTradeCompleted,
    CaravanTradeFulfilled,
    RegionalMerchantStockUpdated,
)


def _to_uuid(val: Any) -> UUID | None:
    if not val:
        return None
    try:
        return UUID(str(val))
    except Exception:
        return None


def calculate_economic_price_modifier(total_deliveries: int, successful_deliveries: int) -> float:
    """Calculate economic price modifier based on caravan delivery success rate.

    - 100% safe deliveries (high supply / trade route secured) -> 0.90 (abundance discount).
    - 100% baseline with low deliveries -> 1.00.
    - Low delivery success rate (scarcity due to ambushes) -> up to 1.50 (scarcity surcharge).
    """
    if total_deliveries <= 0:
        return 1.0
    success_rate = successful_deliveries / total_deliveries
    if success_rate >= 0.99 and total_deliveries >= 2:
        return 0.90
    modifier = 1.0 + (1.0 - success_rate) * 0.50
    return round(max(0.80, min(1.60, modifier)), 2)


class CaravanLedgerState(BaseModel):
    """Event-sourced state for cross-campaign trade routes, caravans, contracts, and merchant stock."""

    shared_world_id: str = ""
    caravans: dict[str, dict[str, Any]] = Field(default_factory=dict)
    contracts: dict[str, dict[str, Any]] = Field(default_factory=dict)
    outpost_stocks: dict[str, dict[str, Any]] = Field(default_factory=dict)


class CaravanLedgerAggregate(DeclarativeAggregate[CaravanLedgerState]):
    """Event-sourced aggregate managing frontier caravan routes and merchant inventories."""

    aggregate_type = "CaravanLedger"
    requires_creation_event = False

    def __init__(self, aggregate_id: Any = None, **kwargs: Any) -> None:
        super().__init__(aggregate_id=aggregate_id, **kwargs)
        if self._state is None:
            self._state = CaravanLedgerState(shared_world_id=str(aggregate_id or ""))

    def _ensure_outpost_stock(self, dest: str) -> dict[str, Any]:
        dest_key = dest.lower()
        if dest_key not in self.state.outpost_stocks:
            self.state.outpost_stocks[dest_key] = {
                "inventory": {},
                "workshop_reagents": {},
                "delivery_stats": {
                    "total_deliveries": 0,
                    "successful_deliveries": 0,
                    "ambushed_deliveries": 0,
                    "success_rate": 1.0,
                },
                "price_modifier": 1.0,
                "last_delivery": None,
            }
        elif "delivery_stats" not in self.state.outpost_stocks[dest_key]:
            self.state.outpost_stocks[dest_key]["delivery_stats"] = {
                "total_deliveries": 0,
                "successful_deliveries": 0,
                "ambushed_deliveries": 0,
                "success_rate": 1.0,
            }
            self.state.outpost_stocks[dest_key]["price_modifier"] = 1.0
        return self.state.outpost_stocks[dest_key]

    @handles(CaravanDispatched)
    def handle_dispatched(self, event: CaravanDispatched) -> None:
        self.state.caravans[event.caravan_id] = {
            "caravan_id": event.caravan_id,
            "contract_id": getattr(event, "contract_id", None),
            "origin_outpost": event.origin_outpost,
            "destination_outpost": event.destination_outpost,
            "cargo": dict(event.cargo),
            "dispatched_by_campaign_id": str(event.dispatched_by_campaign_id),
            "transit_turns": event.transit_turns,
            "status": event.status,
            "dispatched_at": datetime.now(UTC).isoformat(),
        }
        if getattr(event, "contract_id", None) and event.contract_id in self.state.contracts:
            self.state.contracts[event.contract_id]["status"] = "in_transit"
            self.state.contracts[event.contract_id]["caravan_id"] = event.caravan_id

    @handles(CaravanTradeCompleted)
    def handle_trade_completed(self, event: CaravanTradeCompleted) -> None:
        if event.caravan_id in self.state.caravans:
            self.state.caravans[event.caravan_id]["status"] = "completed"
            self.state.caravans[event.caravan_id]["completed_at"] = event.completed_at

        stock = self._ensure_outpost_stock(event.destination_outpost)
        stock["last_delivery"] = event.caravan_id

        for item, qty in event.cargo_delivered.items():
            stock["workshop_reagents"][item] = stock["workshop_reagents"].get(item, 0) + qty

        for key, val in event.unlocked_stock.items():
            stock["inventory"][key] = val

        stats = stock["delivery_stats"]
        stats["total_deliveries"] += 1
        stats["successful_deliveries"] += 1
        stats["success_rate"] = round(stats["successful_deliveries"] / stats["total_deliveries"], 2)
        stock["price_modifier"] = calculate_economic_price_modifier(
            stats["total_deliveries"], stats["successful_deliveries"]
        )

    @handles(CaravanContractPosted)
    def handle_contract_posted(self, event: CaravanContractPosted) -> None:
        self.state.contracts[event.contract_id] = {
            "contract_id": event.contract_id,
            "shared_world_id": str(event.shared_world_id),
            "origin_outpost": event.origin_outpost,
            "destination_outpost": event.destination_outpost,
            "cargo": dict(event.cargo),
            "cargo_value": event.cargo_value,
            "route_risk_level": event.route_risk_level,
            "transit_stages": event.transit_stages,
            "escort_collateral": event.escort_collateral,
            "reward_gold": event.reward_gold,
            "reward_reputation": event.reward_reputation,
            "posted_by_campaign_id": str(event.posted_by_campaign_id),
            "poster_user_id": event.poster_user_id,
            "expires_in_turns": event.expires_in_turns,
            "status": event.status,
            "created_at": event.created_at or datetime.now(UTC).isoformat(),
        }

    @handles(CaravanContractAccepted)
    def handle_contract_accepted(self, event: CaravanContractAccepted) -> None:
        if event.contract_id in self.state.contracts:
            self.state.contracts[event.contract_id]["status"] = "accepted"
            self.state.contracts[event.contract_id]["contractor_campaign_id"] = str(
                event.contractor_campaign_id
            )
            self.state.contracts[event.contract_id]["contractor_party_name"] = (
                event.contractor_party_name
            )

    @handles(CaravanAmbushed)
    def handle_ambushed(self, event: CaravanAmbushed) -> None:
        if event.contract_id in self.state.contracts:
            contract = self.state.contracts[event.contract_id]
            if event.outcome == "caravan_destroyed":
                contract["status"] = "failed"
            dest = contract.get("destination_outpost", "")
            if dest:
                stock = self._ensure_outpost_stock(dest)
                stats = stock["delivery_stats"]
                stats["ambushed_deliveries"] += 1
                if event.outcome == "caravan_destroyed":
                    stats["total_deliveries"] += 1
                    stats["success_rate"] = round(
                        stats["successful_deliveries"] / max(1, stats["total_deliveries"]), 2
                    )
                    stock["price_modifier"] = calculate_economic_price_modifier(
                        stats["total_deliveries"], stats["successful_deliveries"]
                    )

    @handles(CaravanTradeFulfilled)
    def handle_trade_fulfilled(self, event: CaravanTradeFulfilled) -> None:
        if event.contract_id in self.state.contracts:
            self.state.contracts[event.contract_id]["status"] = "fulfilled"
            self.state.contracts[event.contract_id]["fulfilled_at"] = event.fulfilled_at

        stock = self._ensure_outpost_stock(event.destination_outpost)
        stock["last_delivery"] = event.caravan_id

        # Deposit delivered reagents into the settlement workshop
        for item, qty in event.cargo_delivered.items():
            stock["workshop_reagents"][item] = stock["workshop_reagents"].get(item, 0) + qty
            stock["inventory"][f"refined_{item}"] = {
                "name": f"Refined {item.replace('_', ' ').title()}",
                "price_gold": 25,
                "quantity": qty * 2,
                "rarity": "rare",
            }

        stats = stock["delivery_stats"]
        stats["total_deliveries"] += 1
        stats["successful_deliveries"] += 1
        stats["success_rate"] = round(stats["successful_deliveries"] / stats["total_deliveries"], 2)
        stock["price_modifier"] = calculate_economic_price_modifier(
            stats["total_deliveries"], stats["successful_deliveries"]
        )

    @handles(RegionalMerchantStockUpdated)
    def handle_stock_updated(self, event: RegionalMerchantStockUpdated) -> None:
        stock = self._ensure_outpost_stock(event.outpost_name)
        stock["inventory"].update(event.inventory_updates)

    def dispatch_caravan(
        self,
        origin_outpost: str,
        destination_outpost: str,
        cargo: dict[str, int],
        dispatched_by_campaign_id: UUID | str,
        transit_turns: int = 1,
        caravan_id: str | None = None,
        contract_id: str | None = None,
    ) -> str:
        cid = caravan_id or f"caravan_{uuid4().hex[:8]}"
        wid = _to_uuid(self.state.shared_world_id or self.aggregate_id)
        camp_id = _to_uuid(dispatched_by_campaign_id) or str(dispatched_by_campaign_id)
        self.create_event(
            CaravanDispatched,
            contract_id=contract_id,
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

    def complete_contract_delivery(
        self,
        caravan_id: str,
        origin_outpost: str,
        destination_outpost: str,
        cargo_delivered: dict[str, int],
        unlocked_stock: dict[str, Any] | None = None,
    ) -> None:
        """Deliver cargo from a completed mercenary caravan contract and update regional stock."""
        wid = _to_uuid(self.state.shared_world_id or self.aggregate_id)
        now_iso = datetime.now(UTC).isoformat()
        default_unlocked = {}
        for reagent, qty in cargo_delivered.items():
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
            origin_outpost=origin_outpost,
            destination_outpost=destination_outpost,
            cargo_delivered=cargo_delivered,
            unlocked_stock=effective_unlocked,
            completed_at=now_iso,
        )

    def query_contracts(
        self,
        risk_level: str | None = None,
        destination: str | None = None,
        status: str | None = None,
        min_reward: int | None = None,
    ) -> list[dict[str, Any]]:
        """Query available notice board contracts applying optional frontier filters."""
        results: list[dict[str, Any]] = []
        for c in self.state.contracts.values():
            if status and c.get("status") != status:
                continue
            if risk_level and c.get("route_risk_level", "").lower() != risk_level.lower():
                continue
            if destination and c.get("destination_outpost", "").lower() != destination.lower():
                continue
            if min_reward is not None and c.get("reward_gold", 0) < min_reward:
                continue
            results.append(c)
        return results


__all__ = [
    "CaravanLedgerAggregate",
    "CaravanLedgerState",
    "calculate_economic_price_modifier",
]
