"""Caravan domain state models, route risk enums, and manifest schemas.

Part of TASK-0186 / PRD-0007 / US-0058 / ADR-0007.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


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


class CaravanLedgerState(BaseModel):
    """Event-sourced state for cross-campaign trade routes, caravans, contracts, and merchant stock."""

    shared_world_id: str = ""
    caravans: dict[str, dict[str, Any]] = Field(default_factory=dict)
    contracts: dict[str, dict[str, Any]] = Field(default_factory=dict)
    outpost_stocks: dict[str, dict[str, Any]] = Field(default_factory=dict)


__all__ = [
    "CaravanContractState",
    "CaravanLedgerState",
    "_to_uuid",
]
