"""Data models for turf war skirmish simulations and regional unrest."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class SkirmishParticipant(BaseModel):
    """Military attributes of a clashing faction in a skirmish."""

    faction_id: str
    military_strength: int = Field(default=10, ge=1)
    defense_rating: int = Field(default=0, ge=0)
    morale_modifier: int = Field(default=0)


class SkirmishSimulateRequest(BaseModel):
    """Payload to trigger an ad-hoc skirmish simulation between two factions."""

    campaign_id: str
    region_id: str
    contested_node: str
    attacker: SkirmishParticipant
    defender: SkirmishParticipant
    terrain: str = "plains"
    attacker_roll: int | None = Field(default=None, ge=1, le=20)
    defender_roll: int | None = Field(default=None, ge=1, le=20)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SkirmishOutcome(BaseModel):
    """Adjudicated result of a tactical boundary skirmish."""

    skirmish_id: str = Field(default_factory=lambda: f"skm-{uuid4().hex[:8]}")
    winner_faction_id: str
    loser_faction_id: str
    is_stalemate: bool = False
    territory_captured: bool = False
    attacker_casualties: int = 0
    defender_casualties: int = 0
    unrest_delta: int = 0
    narrative: str = ""


class SkirmishSimulateResponse(BaseModel):
    """Response returned upon resolving a skirmish and applying regional unrest."""

    skirmish_id: str
    campaign_id: str
    region_id: str
    contested_node: str
    winner_faction_id: str
    loser_faction_id: str
    is_stalemate: bool = False
    territory_captured: bool = False
    controlling_faction_id: str
    attacker_casualties: int = 0
    defender_casualties: int = 0
    unrest_delta: int = 0
    current_unrest: int = 0
    alert_level: str = "calm"
    security_level: str = "standard"
    economic_friction: float = 0.0
    narrative: str = ""


class RegionalUnrestResponse(BaseModel):
    """Projected regional unrest index, security alert, and economic friction."""

    region_id: str
    campaign_id: str
    controlling_faction_id: str | None = None
    unrest_score: int = 0
    alert_level: str = "calm"
    security_level: str = "standard"
    economic_friction: float = 0.0
    contested_nodes: list[str] = Field(default_factory=list)
    recent_skirmishes: list[dict[str, Any]] = Field(default_factory=list)


class RegionalUnrestState(BaseModel):
    """Event-sourced aggregate state for regional unrest and territorial control."""

    region_id: str
    campaign_id: str = ""
    controlling_faction_id: str | None = None
    unrest_score: int = 0
    alert_level: str = "calm"
    security_level: str = "standard"
    economic_friction: float = 0.0
    contested_nodes: list[str] = Field(default_factory=list)
    recent_skirmishes: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
