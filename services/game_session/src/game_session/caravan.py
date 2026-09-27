"""Caravan Manifest and Frontier Mercenary Contract Domain Aggregate.

Part of TASK-0129 / PRD-0007 / US-0058 / ADR-0001 / ADR-0006 / ADR-0011.
Governed by Hard Invariant 2 (eventsource-py declarative aggregates with @handles).
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
    CaravanTradeFulfilled,
)


def _to_uuid(val: Any) -> UUID | None:
    if not val:
        return None
    try:
        return UUID(str(val))
    except Exception:
        return None


class CaravanContractState(BaseModel):
    """Event-sourced state for an individual frontier mercenary caravan contract."""

    contract_id: str = ""
    shared_world_id: str = ""
    origin_outpost: str = ""
    destination_outpost: str = ""
    cargo: dict[str, int] = Field(default_factory=dict)
    cargo_value: int = 0
    route_risk_level: str = "medium"  # low, medium, high, deadly
    transit_stages: int = 2
    current_stage: int = 0
    escort_collateral: int = 0
    reward_gold: int = 0
    reward_reputation: int = 0
    posted_by_campaign_id: str = ""
    poster_user_id: str | None = None
    contractor_campaign_id: str | None = None
    contractor_party_name: str | None = None
    accepted_by_user_id: str | None = None
    caravan_id: str | None = None
    status: str = "open"  # open, accepted, in_transit, ambushed, fulfilled, failed, cancelled
    ambush_history: list[dict[str, Any]] = Field(default_factory=list)
    cargo_loss_percentage: float = 0.0
    cargo_delivered: dict[str, int] = Field(default_factory=dict)
    cargo_value_delivered: int = 0
    reward_gold_paid: int = 0
    reputation_awarded: int = 0
    expires_in_turns: int = 10
    created_at: str | None = None
    accepted_at: str | None = None
    fulfilled_at: str | None = None


class CaravanContractAggregate(DeclarativeAggregate[CaravanContractState]):
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
        self.state.contract_id = str(event.contract_id)
        self.state.shared_world_id = str(event.shared_world_id)
        self.state.origin_outpost = event.origin_outpost
        self.state.destination_outpost = event.destination_outpost
        self.state.cargo = dict(event.cargo)
        self.state.cargo_value = event.cargo_value
        self.state.route_risk_level = event.route_risk_level
        self.state.transit_stages = event.transit_stages
        self.state.current_stage = 0
        self.state.escort_collateral = event.escort_collateral
        self.state.reward_gold = event.reward_gold
        self.state.reward_reputation = event.reward_reputation
        self.state.posted_by_campaign_id = str(event.posted_by_campaign_id)
        self.state.poster_user_id = event.poster_user_id
        self.state.expires_in_turns = event.expires_in_turns
        self.state.status = event.status
        self.state.created_at = event.created_at or datetime.now(UTC).isoformat()

    @handles(CaravanContractAccepted)
    def handle_contract_accepted(self, event: CaravanContractAccepted) -> None:
        self.state.contractor_campaign_id = str(event.contractor_campaign_id)
        self.state.contractor_party_name = event.contractor_party_name
        self.state.accepted_by_user_id = event.accepted_by_user_id
        self.state.status = event.status
        self.state.accepted_at = event.accepted_at or datetime.now(UTC).isoformat()

    @handles(CaravanDispatched)
    def handle_dispatched(self, event: CaravanDispatched) -> None:
        self.state.caravan_id = event.caravan_id
        self.state.status = "in_transit"
        self.state.current_stage = max(1, self.state.current_stage)

    @handles(CaravanAmbushed)
    def handle_ambushed(self, event: CaravanAmbushed) -> None:
        self.state.ambush_history.append(
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
        if event.outcome == "caravan_destroyed":
            self.state.status = "failed"
            self.state.cargo_loss_percentage = 1.0
        elif event.outcome == "cargo_damaged":
            self.state.cargo_loss_percentage = min(
                1.0, self.state.cargo_loss_percentage + event.cargo_loss_percentage
            )
            self.state.status = "in_transit"
            self.state.current_stage = min(self.state.transit_stages, event.stage_index + 1)
        else:  # repelled
            self.state.status = "in_transit"
            self.state.current_stage = min(self.state.transit_stages, event.stage_index + 1)

    @handles(CaravanTradeFulfilled)
    def handle_trade_fulfilled(self, event: CaravanTradeFulfilled) -> None:
        self.state.status = event.status
        self.state.cargo_delivered = dict(event.cargo_delivered)
        self.state.cargo_value_delivered = event.cargo_value_delivered
        self.state.reward_gold_paid = event.reward_gold_paid
        self.state.reputation_awarded = event.reputation_awarded
        self.state.fulfilled_at = event.fulfilled_at or datetime.now(UTC).isoformat()
        self.state.current_stage = self.state.transit_stages

    def post_contract(
        self,
        shared_world_id: UUID | str,
        origin_outpost: str,
        destination_outpost: str,
        cargo: dict[str, int],
        cargo_value: int,
        posted_by_campaign_id: UUID | str,
        route_risk_level: str = "medium",
        transit_stages: int = 2,
        escort_collateral: int = 50,
        reward_gold: int = 150,
        reward_reputation: int = 10,
        poster_user_id: str | None = None,
        expires_in_turns: int = 10,
    ) -> str:
        """Post a new asynchronous mercenary escort contract to the shared world notice board."""
        if origin_outpost.strip().lower() == destination_outpost.strip().lower():
            raise ValueError("Origin and destination outposts must be distinct")
        if not cargo or sum(cargo.values()) <= 0:
            raise ValueError("Caravan cargo manifest must contain at least one item")
        if cargo_value <= 0:
            raise ValueError("Cargo value must be greater than zero")

        cid = str(self.aggregate_id)
        wid = _to_uuid(shared_world_id) or str(shared_world_id)
        camp_id = _to_uuid(posted_by_campaign_id) or str(posted_by_campaign_id)
        now_iso = datetime.now(UTC).isoformat()

        self.create_event(
            CaravanContractPosted,
            contract_id=cid,
            shared_world_id=wid,
            origin_outpost=origin_outpost.strip(),
            destination_outpost=destination_outpost.strip(),
            cargo=cargo,
            cargo_value=cargo_value,
            route_risk_level=route_risk_level,
            transit_stages=transit_stages,
            escort_collateral=escort_collateral,
            reward_gold=reward_gold,
            reward_reputation=reward_reputation,
            posted_by_campaign_id=camp_id,
            poster_user_id=poster_user_id,
            expires_in_turns=expires_in_turns,
            status="open",
            created_at=now_iso,
        )
        return cid

    def accept_contract(
        self,
        contractor_campaign_id: UUID | str,
        contractor_party_name: str,
        accepted_by_user_id: str | None = None,
    ) -> None:
        """Claim and accept an open caravan escort contract on behalf of an adventuring party."""
        if self.state.status != "open":
            raise ValueError(f"Cannot accept contract with status '{self.state.status}'")

        wid = _to_uuid(self.state.shared_world_id) or str(self.state.shared_world_id)
        cid = self.state.contract_id or str(self.aggregate_id)
        camp_id = _to_uuid(contractor_campaign_id) or str(contractor_campaign_id)
        now_iso = datetime.now(UTC).isoformat()

        self.create_event(
            CaravanContractAccepted,
            contract_id=cid,
            shared_world_id=wid,
            contractor_campaign_id=camp_id,
            contractor_party_name=contractor_party_name.strip(),
            accepted_by_user_id=accepted_by_user_id,
            status="accepted",
            accepted_at=now_iso,
        )

    def dispatch_caravan(
        self,
        caravan_id: str | None = None,
        dispatched_by_campaign_id: UUID | str | None = None,
    ) -> str:
        """Dispatch the caravan onto the frontier route toward its destination outpost."""
        if self.state.status != "accepted":
            raise ValueError(
                f"Cannot dispatch caravan for contract with status '{self.state.status}'"
            )

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
        """Record the tactical combat outcome of a wilderness ambush or environmental hazard."""
        if self.state.status not in ("in_transit", "ambushed"):
            raise ValueError(f"Cannot report ambush for contract with status '{self.state.status}'")

        if outcome not in ("repelled", "cargo_damaged", "caravan_destroyed"):
            raise ValueError(f"Invalid ambush outcome: '{outcome}'")

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
        if self.state.status not in ("in_transit", "ambushed"):
            raise ValueError(
                f"Cannot fulfill contract with status '{self.state.status}' (must be in transit)"
            )

        cid = self.state.contract_id or str(self.aggregate_id)
        wid = _to_uuid(self.state.shared_world_id) or str(self.state.shared_world_id)
        now_iso = datetime.now(UTC).isoformat()

        # Compute surviving cargo delivered and payout calculations
        loss = min(1.0, max(0.0, self.state.cargo_loss_percentage))
        surviving_ratio = 1.0 - loss

        delivered_cargo = {
            item: max(0, int(round(qty * surviving_ratio)))
            for item, qty in self.state.cargo.items()
        }
        cargo_value_delivered = int(round(self.state.cargo_value * surviving_ratio))
        gold_payout = (
            int(round(self.state.reward_gold * (1.0 - (loss * 0.5)))) + self.state.escort_collateral
        )
        reputation = max(1, int(round(self.state.reward_reputation * surviving_ratio)))

        self.create_event(
            CaravanTradeFulfilled,
            contract_id=cid,
            shared_world_id=wid,
            caravan_id=self.state.caravan_id or f"caravan_{cid[:8]}",
            origin_outpost=self.state.origin_outpost,
            destination_outpost=self.state.destination_outpost,
            cargo_delivered=delivered_cargo,
            cargo_value_delivered=cargo_value_delivered,
            reward_gold_paid=gold_payout,
            reputation_awarded=reputation,
            contractor_campaign_id=_to_uuid(self.state.contractor_campaign_id)
            or str(self.state.contractor_campaign_id or ""),
            fulfilled_at=now_iso,
            status="fulfilled",
        )

        return {
            "contract_id": cid,
            "cargo_delivered": delivered_cargo,
            "cargo_value_delivered": cargo_value_delivered,
            "reward_gold_paid": gold_payout,
            "reputation_awarded": reputation,
            "status": "fulfilled",
        }


__all__ = [
    "CaravanContractAggregate",
    "CaravanContractState",
]
