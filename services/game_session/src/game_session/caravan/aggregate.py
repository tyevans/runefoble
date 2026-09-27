"""Caravan Manifest and Frontier Mercenary Contract Domain Aggregate.

Part of TASK-0186 / PRD-0007 / US-0058 / ADR-0007 / ADR-0011.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from game_session.caravan.board_operations import CaravanBoardOperationsMixin
from game_session.caravan.models import CaravanContractState, _to_uuid
from game_session.caravan.transit import calculate_transit_ambush_progress
from game_session.caravan.transit_operations import CaravanTransitOperationsMixin
from runefoble_events.west_marches import (
    CaravanAmbushed,
    CaravanContractAccepted,
    CaravanContractPosted,
    CaravanDispatched,
    CaravanTradeFulfilled,
)


class CaravanContractAggregate(
    CaravanBoardOperationsMixin,
    CaravanTransitOperationsMixin,
    DeclarativeAggregate[CaravanContractState],
):
    """Event-sourced aggregate managing caravan manifests, escrow, transit stages, and escorts."""

    aggregate_type = "CaravanContract"
    requires_creation_event = False

    def __init__(self, aggregate_id: Any = None, **kwargs: Any) -> None:
        agg_uuid = _to_uuid(aggregate_id) or uuid4()
        super().__init__(aggregate_id=agg_uuid, **kwargs)
        if self._state is None:
            self._state = CaravanContractState(contract_id=str(agg_uuid))

    @handles(CaravanContractPosted)
    def handle_contract_posted(self, event: CaravanContractPosted) -> None:
        s = self.state
        s.contract_id, s.shared_world_id = str(event.contract_id), str(event.shared_world_id)
        s.origin_outpost, s.destination_outpost = event.origin_outpost, event.destination_outpost
        s.cargo, s.cargo_value = dict(event.cargo), event.cargo_value
        s.route_risk_level, s.transit_stages, s.current_stage = (
            event.route_risk_level,
            event.transit_stages,
            0,
        )
        s.escort_collateral = event.escort_collateral
        s.reward_gold, s.reward_reputation = event.reward_gold, event.reward_reputation
        s.posted_by_campaign_id = str(event.posted_by_campaign_id)
        s.poster_user_id = event.poster_user_id
        s.expires_in_turns, s.status = event.expires_in_turns, event.status
        s.created_at = event.created_at or datetime.now(UTC).isoformat()

    @handles(CaravanContractAccepted)
    def handle_contract_accepted(self, event: CaravanContractAccepted) -> None:
        s = self.state
        s.contractor_campaign_id = str(event.contractor_campaign_id)
        s.contractor_party_name = event.contractor_party_name
        s.accepted_by_user_id = event.accepted_by_user_id
        s.status = event.status
        s.accepted_at = event.accepted_at or datetime.now(UTC).isoformat()

    @handles(CaravanDispatched)
    def handle_dispatched(self, event: CaravanDispatched) -> None:
        self.state.caravan_id = event.caravan_id
        self.state.status = "in_transit"
        self.state.current_stage = max(1, self.state.current_stage)

    @handles(CaravanAmbushed)
    def handle_ambushed(self, event: CaravanAmbushed) -> None:
        s = self.state
        s.ambush_history.append(
            {
                "stage_index": event.stage_index,
                "ambush_type": event.ambush_type,
                "danger_level": event.danger_level,
                "outcome": event.outcome,
                "cargo_loss_percentage": event.cargo_loss_percentage,
                "reported_by_campaign_id": str(event.reported_by_campaign_id),
                "notes": event.notes,
            }
        )
        status, stage, loss = calculate_transit_ambush_progress(
            s.current_stage,
            s.transit_stages,
            event.stage_index,
            event.outcome,
            s.cargo_loss_percentage,
            event.cargo_loss_percentage,
        )
        s.status, s.current_stage, s.cargo_loss_percentage = status, stage, loss

    @handles(CaravanTradeFulfilled)
    def handle_trade_fulfilled(self, event: CaravanTradeFulfilled) -> None:
        s = self.state
        s.status, s.cargo_delivered = event.status, dict(event.cargo_delivered)
        s.cargo_value_delivered = event.cargo_value_delivered
        s.reward_gold_paid = event.reward_gold_paid
        s.reputation_awarded = event.reputation_awarded
        s.fulfilled_at = event.fulfilled_at or datetime.now(UTC).isoformat()
        s.current_stage = s.transit_stages


__all__ = ["CaravanContractAggregate"]
