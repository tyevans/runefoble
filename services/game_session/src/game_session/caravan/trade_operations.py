"""Operations and trade dispatch mixin for regional caravan ledger.

Part of TASK-0186 / TASK-0127 / TASK-0129 / PRD-0007 / US-0058 / ADR-0007 / ADR-0011.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from game_session.caravan.escrow import (
    filter_contracts,
    generate_default_refined_stock,
)
from game_session.caravan.models import CaravanLedgerState, _to_uuid
from runefoble_events.west_marches import (
    CaravanDispatched,
    CaravanTradeCompleted,
)


class CaravanTradeOperationsMixin:
    """Operations mixin providing caravan dispatching, trade completion, and contract queries."""

    _state: CaravanLedgerState | None
    state: CaravanLedgerState
    aggregate_id: Any
    create_event: Any

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
        """Dispatch a resource caravan between frontier settlement outposts."""
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
        """Finalize standard caravan trade arrival and deposit unlocked merchant stock."""
        if caravan_id not in self.state.caravans:
            raise ValueError(f"Caravan '{caravan_id}' not found")
        caravan = self.state.caravans[caravan_id]
        if caravan["status"] == "completed":
            return caravan

        wid = _to_uuid(self.state.shared_world_id or self.aggregate_id)
        delivered_cargo = dict(caravan["cargo"])
        effective_unlocked = (
            unlocked_stock
            if unlocked_stock is not None
            else generate_default_refined_stock(delivered_cargo)
        )

        self.create_event(
            CaravanTradeCompleted,
            shared_world_id=wid,
            caravan_id=caravan_id,
            origin_outpost=caravan["origin_outpost"],
            destination_outpost=caravan["destination_outpost"],
            cargo_delivered=delivered_cargo,
            unlocked_stock=effective_unlocked,
            completed_at=datetime.now(UTC).isoformat(),
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
        effective_unlocked = (
            unlocked_stock
            if unlocked_stock is not None
            else generate_default_refined_stock(cargo_delivered)
        )

        self.create_event(
            CaravanTradeCompleted,
            shared_world_id=wid,
            caravan_id=caravan_id,
            origin_outpost=origin_outpost,
            destination_outpost=destination_outpost,
            cargo_delivered=cargo_delivered,
            unlocked_stock=effective_unlocked,
            completed_at=datetime.now(UTC).isoformat(),
        )

    def query_contracts(
        self,
        risk_level: str | None = None,
        destination: str | None = None,
        status: str | None = None,
        min_reward: int | None = None,
    ) -> list[dict[str, Any]]:
        """Query available notice board contracts applying optional frontier filters."""
        return filter_contracts(
            self.state.contracts,
            risk_level=risk_level,
            destination=destination,
            status=status,
            min_reward=min_reward,
        )


__all__ = ["CaravanTradeOperationsMixin"]
