"""Board posting and contract acceptance mixin for caravan contracts.

Part of TASK-0186 / PRD-0007 / US-0058 / ADR-0007 / ADR-0011.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from game_session.caravan.models import CaravanContractState, _to_uuid
from game_session.caravan.transit import (
    validate_can_accept,
    validate_contract_post,
)
from runefoble_events.west_marches import (
    CaravanContractAccepted,
    CaravanContractPosted,
)


class CaravanBoardOperationsMixin:
    """Operations mixin providing contract posting and mercenary acceptance."""

    _state: CaravanContractState | None
    state: CaravanContractState
    aggregate_id: Any
    create_event: Any

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
        validate_contract_post(origin_outpost, destination_outpost, cargo, cargo_value)
        cid = str(self.aggregate_id)
        wid = _to_uuid(shared_world_id) or str(shared_world_id)
        camp_id = _to_uuid(posted_by_campaign_id) or str(posted_by_campaign_id)

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
            created_at=datetime.now(UTC).isoformat(),
        )
        return cid

    def accept_contract(
        self,
        contractor_campaign_id: UUID | str,
        contractor_party_name: str,
        accepted_by_user_id: str | None = None,
    ) -> None:
        """Claim and accept an open caravan escort contract on behalf of an adventuring party."""
        validate_can_accept(self.state.status)
        wid = _to_uuid(self.state.shared_world_id) or str(self.state.shared_world_id)
        cid = self.state.contract_id or str(self.aggregate_id)
        camp_id = _to_uuid(contractor_campaign_id) or str(contractor_campaign_id)

        self.create_event(
            CaravanContractAccepted,
            contract_id=cid,
            shared_world_id=wid,
            contractor_campaign_id=camp_id,
            contractor_party_name=contractor_party_name.strip(),
            accepted_by_user_id=accepted_by_user_id,
            status="accepted",
            accepted_at=datetime.now(UTC).isoformat(),
        )


__all__ = ["CaravanBoardOperationsMixin"]
