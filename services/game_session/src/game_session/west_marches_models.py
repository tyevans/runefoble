"""Request and response models for West Marches and Caravan Trading APIs.

Part of TASK-0127 / PRD-0007 / US-0058 / ADR-0001 / ADR-0006.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CreateSharedWorldRequest(BaseModel):
    name: str = "The Frontier Marches"
    frontier_region: str = "The Untamed Wilds"
    description: str = ""


class RegisterCampaignRequest(BaseModel):
    campaign_id: str
    party_name: str


class RecordDiscoveryRequest(BaseModel):
    name: str
    discovery_type: str = "dungeon"
    coordinates: dict[str, float]
    discovered_by_campaign_id: str
    discovered_by_party_name: str
    description: str = ""
    danger_level: int = 1
    discovery_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EstablishOutpostRequest(BaseModel):
    name: str
    region: str
    contributing_campaign_id: str
    outpost_id: str | None = None
    facilities: dict[str, int] | None = None
    resources_contributed: dict[str, int] | None = None


class PostNoticeRequest(BaseModel):
    campaign_id: str
    author_name: str
    title: str
    content: str
    notice_type: str = "bounty"
    bounty_reward: int | str = 0


class DispatchCaravanRequest(BaseModel):
    origin_outpost: str
    destination_outpost: str
    cargo: dict[str, int]
    dispatched_by_campaign_id: str
    transit_turns: int = 1


class CompleteCaravanRequest(BaseModel):
    unlocked_stock: dict[str, Any] | None = None


class PostCaravanContractRequest(BaseModel):
    origin_outpost: str
    destination_outpost: str
    cargo: dict[str, int]
    cargo_value: int
    route_risk_level: str = "medium"
    transit_stages: int = 2
    escort_collateral: int = 50
    reward_gold: int = 150
    reward_reputation: int = 10
    posted_by_campaign_id: str
    expires_in_turns: int = 10


class AcceptCaravanContractRequest(BaseModel):
    contractor_campaign_id: str
    contractor_party_name: str


class DispatchContractCaravanRequest(BaseModel):
    caravan_id: str | None = None
    dispatched_by_campaign_id: str | None = None


class ReportAmbushRequest(BaseModel):
    stage_index: int = 1
    ambush_type: str = "bandit_raid"
    danger_level: int = 1
    outcome: str = "repelled"
    cargo_loss_percentage: float = 0.0
    reported_by_campaign_id: str = ""
    notes: str = ""


class FulfillContractRequest(BaseModel):
    unlocked_stock: dict[str, Any] | None = None


__all__ = [
    "AcceptCaravanContractRequest",
    "CompleteCaravanRequest",
    "CreateSharedWorldRequest",
    "DispatchCaravanRequest",
    "DispatchContractCaravanRequest",
    "EstablishOutpostRequest",
    "FulfillContractRequest",
    "PostCaravanContractRequest",
    "PostNoticeRequest",
    "RecordDiscoveryRequest",
    "RegisterCampaignRequest",
    "ReportAmbushRequest",
]
