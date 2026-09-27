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


__all__ = [
    "CompleteCaravanRequest",
    "CreateSharedWorldRequest",
    "DispatchCaravanRequest",
    "EstablishOutpostRequest",
    "PostNoticeRequest",
    "RecordDiscoveryRequest",
    "RegisterCampaignRequest",
]
