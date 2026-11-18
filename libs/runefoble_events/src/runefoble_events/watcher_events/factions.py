"""Faction agenda, geopolitical simulation, and world tick domain events."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event("runefoble.events.watcher.faction_created")
class FactionCreated(BaseRunefobleEvent):
    aggregate_type: str = "Faction"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.watcher.faction_created"
    campaign_id: str
    faction_id: str
    name: str
    influence: int = 50
    resources: int = 50
    disposition: str = "neutral"
    active_goal: str = ""
    rival_faction_ids: list[str] = Field(default_factory=list)
    territory: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


@register_event("runefoble.events.watcher.faction_agenda_set")
class FactionAgendaSet(BaseRunefobleEvent):
    aggregate_type: str = "Faction"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.watcher.faction_agenda_set"
    campaign_id: str
    faction_id: str
    active_goal: str
    target_progress: int = 100
    current_progress: int = 0
    target_faction_or_location: str | None = None


@register_event("runefoble.events.watcher.faction_agenda_advanced")
class FactionAgendaAdvanced(BaseRunefobleEvent):
    aggregate_type: str = "Faction"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.watcher.faction_agenda_advanced"
    campaign_id: str
    faction_id: str
    faction_name: str
    agenda_name: str
    roll: int
    modifier: int
    dc: int
    outcome: str
    progress_delta: int
    current_progress: int
    target_progress: int
    narrative: str


@register_event("runefoble.events.watcher.geopolitical_shift_occurred")
class GeopoliticalShiftOccurred(BaseRunefobleEvent):
    aggregate_type: str = "Faction"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.watcher.geopolitical_shift_occurred"
    campaign_id: str
    faction_id: str
    territory: str
    shift_type: str
    description: str
    severity: str = "moderate"
    ripple_effects: list[str] = Field(default_factory=list)


@register_event("runefoble.events.watcher.campaign_faction_registered")
class CampaignFactionRegistered(BaseRunefobleEvent):
    """A faction joined a campaign's simulation registry."""

    aggregate_type: str = "CampaignWorld"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.watcher.campaign_faction_registered"
    campaign_id: str
    faction_id: str


@register_event("runefoble.events.watcher.world_tick_executed")
class WorldTickExecuted(BaseRunefobleEvent):
    aggregate_type: str = "CampaignWorld"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.watcher.world_tick_executed"
    campaign_id: str
    tick_number: int
    intelligence_bulletin: str
    factions_simulated: list[str] = Field(default_factory=list)
    shifts: list[dict[str, Any]] = Field(default_factory=list)
    rumors: list[str] = Field(default_factory=list)


__all__ = [
    "CampaignFactionRegistered",
    "FactionAgendaAdvanced",
    "FactionAgendaSet",
    "FactionCreated",
    "GeopoliticalShiftOccurred",
    "WorldTickExecuted",
]
