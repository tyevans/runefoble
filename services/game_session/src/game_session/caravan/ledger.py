"""Caravan trade and resource ledger aggregate for West Marches frontier economy.

Part of TASK-0186 / TASK-0127 / TASK-0129 / PRD-0007 / US-0058 / ADR-0007 / ADR-0011.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from game_session.caravan.escrow import (
    apply_ambush_stats_to_stock,
    apply_delivery_success_to_stock,
    ensure_outpost_stock_entry,
    generate_default_refined_stock,
)
from game_session.caravan.models import CaravanLedgerState
from game_session.caravan.trade_operations import CaravanTradeOperationsMixin
from runefoble_events.west_marches import (
    CaravanAmbushed,
    CaravanContractAccepted,
    CaravanContractPosted,
    CaravanDispatched,
    CaravanTradeCompleted,
    CaravanTradeFulfilled,
    RegionalMerchantStockUpdated,
)


class CaravanLedgerAggregate(
    CaravanTradeOperationsMixin,
    DeclarativeAggregate[CaravanLedgerState],
):
    """Event-sourced aggregate managing frontier caravan routes and merchant inventories."""

    aggregate_type = "CaravanLedger"
    requires_creation_event = False

    def __init__(self, aggregate_id: Any = None, **kwargs: Any) -> None:
        super().__init__(aggregate_id=aggregate_id, **kwargs)
        if self._state is None:
            self._state = CaravanLedgerState(shared_world_id=str(aggregate_id or ""))

    def _ensure_outpost_stock(self, dest: str) -> dict[str, Any]:
        return ensure_outpost_stock_entry(self.state.outpost_stocks, dest)

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
        cid = getattr(event, "contract_id", None)
        if cid and cid in self.state.contracts:
            self.state.contracts[cid]["status"] = "in_transit"
            self.state.contracts[cid]["caravan_id"] = event.caravan_id

    @handles(CaravanTradeCompleted)
    def handle_trade_completed(self, event: CaravanTradeCompleted) -> None:
        if event.caravan_id in self.state.caravans:
            self.state.caravans[event.caravan_id]["status"] = "completed"
            self.state.caravans[event.caravan_id]["completed_at"] = event.completed_at

        stock = self._ensure_outpost_stock(event.destination_outpost)
        apply_delivery_success_to_stock(
            stock, event.caravan_id, event.cargo_delivered, event.unlocked_stock
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
            c = self.state.contracts[event.contract_id]
            c["status"] = "accepted"
            c["contractor_campaign_id"] = str(event.contractor_campaign_id)
            c["contractor_party_name"] = event.contractor_party_name

    @handles(CaravanAmbushed)
    def handle_ambushed(self, event: CaravanAmbushed) -> None:
        if event.contract_id in self.state.contracts:
            contract = self.state.contracts[event.contract_id]
            if event.outcome == "caravan_destroyed":
                contract["status"] = "failed"
            dest = contract.get("destination_outpost", "")
            if dest:
                stock = self._ensure_outpost_stock(dest)
                apply_ambush_stats_to_stock(stock, event.outcome)

    @handles(CaravanTradeFulfilled)
    def handle_trade_fulfilled(self, event: CaravanTradeFulfilled) -> None:
        if event.contract_id in self.state.contracts:
            c = self.state.contracts[event.contract_id]
            c["status"] = "fulfilled"
            c["fulfilled_at"] = event.fulfilled_at

        stock = self._ensure_outpost_stock(event.destination_outpost)
        unlocked = generate_default_refined_stock(event.cargo_delivered)
        apply_delivery_success_to_stock(stock, event.caravan_id, event.cargo_delivered, unlocked)

    @handles(RegionalMerchantStockUpdated)
    def handle_stock_updated(self, event: RegionalMerchantStockUpdated) -> None:
        stock = self._ensure_outpost_stock(event.outpost_name)
        stock["inventory"].update(event.inventory_updates)


__all__ = ["CaravanLedgerAggregate"]
