"""Pydantic schemas for faction treasury, mercenaries, contraband, and bribery."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class MercenaryUnit(BaseModel):
    """A hired mercenary detachment under faction payroll."""

    unit_id: str = Field(default_factory=lambda: uuid4().hex[:8])
    name: str
    unit_type: str = "infantry"
    count: int = Field(default=1, ge=1)
    cost_per_unit: int = Field(default=10, ge=0)
    upkeep_per_tick: int = Field(default=1, ge=0)


class ContrabandItem(BaseModel):
    """Illicit goods or smuggled items tracked in faction stores."""

    item_id: str = Field(default_factory=lambda: uuid4().hex[:8])
    name: str
    category: str = "illicit"
    quantity: int = Field(default=1, ge=1)
    value: int = Field(default=10, ge=0)


class FactionResourceState(BaseModel):
    """Aggregate state of faction assets, mercenaries, and contraband."""

    faction_id: str
    campaign_id: str = ""
    treasury: int = 100
    contraband_score: int = 0
    total_mercenaries: int = 0
    mercenaries: list[MercenaryUnit] = Field(default_factory=list)
    contraband: list[ContrabandItem] = Field(default_factory=list)
    history: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResourceAdjustRequest(BaseModel):
    """Request payload to adjust treasury or contraband assets."""

    treasury_delta: int = 0
    contraband_delta: int = 0
    reason: str = ""
    campaign_id: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class MercenaryRecruitRequest(BaseModel):
    """Request payload to hire mercenary units."""

    unit_name: str
    unit_type: str = "infantry"
    count: int = Field(default=1, ge=1)
    cost_per_unit: int = Field(default=10, ge=0)
    upkeep_per_tick: int = Field(default=1, ge=0)
    campaign_id: str = ""


class BriberyAttemptRequest(BaseModel):
    """Request payload to execute a bribery check against an NPC or official."""

    target_name: str
    target_role: str = "official"
    bribe_amount: int = Field(ge=0)
    target_loyalty: str = "neutral"
    counter_bribe: int = 0
    roll: int | None = None
    campaign_id: str = ""


class BriberyAttemptResponse(BaseModel):
    """Outcome of a resolved bribery check."""

    faction_id: str
    target_name: str
    bribe_amount: int
    dc: int
    roll: int
    modifier: int
    total_roll: int
    success: bool
    outcome: str
    narrative: str
    remaining_treasury: int


class FactionResourceResponse(BaseModel):
    """Public serialized view of a faction's economic standing."""

    faction_id: str
    campaign_id: str
    treasury: int
    contraband_score: int
    mercenaries_count: int
    upkeep_cost: int
    mercenaries: list[MercenaryUnit] = Field(default_factory=list)
    contraband: list[ContrabandItem] = Field(default_factory=list)
