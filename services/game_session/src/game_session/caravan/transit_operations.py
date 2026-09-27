"""Transit, hazard progression, and fulfillment mixin for caravan contracts.

Part of TASK-0186 / PRD-0007 / US-0058 / ADR-0007 / ADR-0011.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from game_session.caravan.models import CaravanContractState, _to_uuid
from game_session.caravan.transit import (
    calculate_contract_payout,
    validate_ambush_outcome,
    validate_can_dispatch,
    validate_can_fulfill,
)
from runefoble_events.west_marches import (
    CaravanAmbushed,
    CaravanDispatched,
    CaravanTradeFulfilled,
)


class CaravanTransitOperationsMixin:
    """Operations mixin providing caravan dispatch, hazard ambush recording, and fulfillment."""

    _state: CaravanContractState | None
    state: CaravanContractState
    aggregate_id: Any
    create_event: Any

    def dispatch_caravan(
        self,
        caravan_id: str | None = None,
        dispatched_by_campaign_id: UUID | str | None = None,
    ) -> str:
        """Dispatch the caravan onto the frontier route toward its destination outpost."""
        validate_can_dispatch(self.state.status)
        cid = self.state.contract_id or str(self.aggregate_id)
        caravan_cid = caravan_id or f"caravan_{uuid4().hex[:8]}"
        wid = _to_uuid(self.state.shared_world_id) or str(self.state.shared_world_id)
        camp_id = (
            _to_uuid(dispatched_by_campaign_id)
            or self.state.contractor_campaign_id
            or self.state.posted_by_campaign_id
        )

        self.create_event(
            CaravanDispatched,
            contract_id=cid,
            shared_world_id=wid,
            caravan_id=caravan_cid,
            origin_outpost=self.state.origin_outpost,
            destination_outpost=self.state.destination_outpost,
            cargo=self.state.cargo,
            dispatched_by_campaign_id=_to_uuid(camp_id) or str(camp_id),
            transit_turns=self.state.transit_stages,
            status="in_transit",
        )
        return caravan_cid

    def report_ambush_outcome(
        self,
        stage_index: int,
        ambush_type: str = "bandit_raid",
        danger_level: int = 1,
        outcome: str = "repelled",
        cargo_loss_percentage: float = 0.0,
        reported_by_campaign_id: UUID | str = "",
        notes: str = "",
    ) -> None:
        """Record the tactical combat outcome of a wilderness ambush or hazard."""
        validate_ambush_outcome(self.state.status, outcome)
        cid = self.state.contract_id or str(self.aggregate_id)
        wid = _to_uuid(self.state.shared_world_id) or str(self.state.shared_world_id)
        camp_id = _to_uuid(reported_by_campaign_id) or str(reported_by_campaign_id)

        self.create_event(
            CaravanAmbushed,
            contract_id=cid,
            shared_world_id=wid,
            caravan_id=self.state.caravan_id or f"caravan_{cid[:8]}",
            stage_index=stage_index,
            ambush_type=ambush_type,
            danger_level=danger_level,
            outcome=outcome,
            cargo_loss_percentage=max(0.0, min(1.0, cargo_loss_percentage)),
            reported_by_campaign_id=camp_id,
            notes=notes,
        )

    def fulfill_contract(self) -> dict[str, Any]:
        """Deliver arriving caravan cargo, pay reward escrow, and fulfill mercenary contract."""
        validate_can_fulfill(self.state.status)
        cid = self.state.contract_id or str(self.aggregate_id)
        wid = _to_uuid(self.state.shared_world_id) or str(self.state.shared_world_id)
        payout = calculate_contract_payout(
            self.state.cargo,
            self.state.cargo_value,
            self.state.reward_gold,
            self.state.escort_collateral,
            self.state.reward_reputation,
            self.state.cargo_loss_percentage,
        )

        self.create_event(
            CaravanTradeFulfilled,
            contract_id=cid,
            shared_world_id=wid,
            caravan_id=self.state.caravan_id or f"caravan_{cid[:8]}",
            origin_outpost=self.state.origin_outpost,
            destination_outpost=self.state.destination_outpost,
            cargo_delivered=payout["cargo_delivered"],
            cargo_value_delivered=payout["cargo_value_delivered"],
            reward_gold_paid=payout["reward_gold_paid"],
            reputation_awarded=payout["reputation_awarded"],
            contractor_campaign_id=_to_uuid(self.state.contractor_campaign_id)
            or str(self.state.contractor_campaign_id or ""),
            fulfilled_at=datetime.now(UTC).isoformat(),
            status="fulfilled",
        )
        return {"contract_id": cid, **payout, "status": "fulfilled"}


__all__ = ["CaravanTransitOperationsMixin"]
