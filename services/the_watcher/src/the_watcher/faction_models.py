"""Pydantic schemas and models for autonomous faction simulation and world ticks."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FactionCreateRequest(BaseModel):
    """Payload to register a new faction in a campaign."""

    name: str
    influence: int = 50
    resources: int = 50
    disposition: str = "neutral"
    active_goal: str = ""
    rival_faction_ids: list[str] = Field(default_factory=list)
    territory: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class FactionResponse(BaseModel):
    """Serialized representation of a faction's aggregate state."""

    faction_id: str
    campaign_id: str
    name: str
    influence: int
    resources: int
    disposition: str
    active_goal: str
    goal_progress: int
    goal_target: int
    rival_faction_ids: list[str] = Field(default_factory=list)
    territory: str = ""
    shifts: list[dict[str, Any]] = Field(default_factory=list)
    history: list[dict[str, Any]] = Field(default_factory=list)


class WorldTickRequest(BaseModel):
    """Payload to trigger an autonomous downtime world progression tick."""

    regional_stability: int = Field(default=50, ge=0, le=100)
    random_seed: int | None = None
    custom_rumors: list[str] | None = None
    ticks: int = Field(default=1, ge=1, le=10)
    notes: str | None = None


class GeopoliticalShiftModel(BaseModel):
    """A territorial, trade, or political shift caused by faction agenda completion."""

    faction_id: str
    faction_name: str
    territory: str
    shift_type: str
    description: str
    severity: str = "moderate"
    ripple_effects: list[str] = Field(default_factory=list)


class WorldTickResponse(BaseModel):
    """Comprehensive output of an executed world progression tick with DM intelligence."""

    campaign_id: str
    tick_number: int
    intelligence_bulletin: str
    factions: list[FactionResponse] = Field(default_factory=list)
    shifts: list[GeopoliticalShiftModel] = Field(default_factory=list)
    tavern_rumors: list[str] = Field(default_factory=list)
    timestamp: str
