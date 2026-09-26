"""Pydantic schemas and response models for Campaign Analytics & Chronicle Archive."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HeatmapCell(BaseModel):
    """Aggregated spatial heatmap cell."""

    x: int
    y: int
    density: int = Field(default=0, description="Total interaction weight/density")
    movement_count: int = Field(default=0, description="Number of token movements into cell")
    damage_total: int = Field(default=0, description="Total damage sustained in cell")
    hit_count: int = Field(default=0, description="Number of strikes landed in cell")
    knockout_count: int = Field(default=0, description="Number of knockouts occurred in cell")


class CampaignHeatmapResponse(BaseModel):
    """Response model for spatial coordinate hit/damage densities."""

    campaign_id: str
    session_id: str | None = None
    cell_size: int = 5
    metric: str = "all"
    total_points: int = 0
    max_density: int = 0
    cells: list[HeatmapCell] = Field(default_factory=list)


class CombatantPerformance(BaseModel):
    """Tactical combatant performance summary."""

    combatant_id: str
    combatant_name: str
    damage_dealt: int = 0
    damage_taken: int = 0
    healing_provided: int = 0
    critical_hits: int = 0
    fumbles: int = 0
    turns_taken: int = 0
    mvp_score: float = 0.0


class MvpAward(BaseModel):
    """Specific MVP award conferred on a player or combatant."""

    title: str
    recipient_id: str
    recipient_name: str
    metric_name: str
    score: float | int
    description: str


class CampaignMvpResponse(BaseModel):
    """Response model for per-encounter / campaign MVP statistics and awards."""

    campaign_id: str
    session_id: str | None = None
    encounter_id: str | None = None
    overall_mvp: MvpAward | None = None
    awards: list[MvpAward] = Field(default_factory=list)
    combatants: list[CombatantPerformance] = Field(default_factory=list)


class TimelineMilestone(BaseModel):
    """Chronological event milestone linking sessions, boss encounters, and recaps."""

    id: str
    campaign_id: str
    session_id: str
    type: str = Field(description="Milestone category, e.g. session_start, boss_encounter, recap")
    title: str
    description: str
    timestamp: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class CampaignTimelineResponse(BaseModel):
    """Response model for campaign chronicle milestone timeline."""

    campaign_id: str
    session_id: str | None = None
    total_milestones: int = 0
    milestones: list[TimelineMilestone] = Field(default_factory=list)
