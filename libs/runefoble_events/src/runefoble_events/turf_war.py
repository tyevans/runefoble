"""Domain events for contested faction skirmishes, territory capture, and regional unrest."""

from __future__ import annotations

from typing import Any, ClassVar
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event("runefoble.events.watcher.faction_skirmish_resolved")
class FactionSkirmishResolvedEvent(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "RegionalUnrest"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.watcher.faction_skirmish_resolved"
    skirmish_id: str
    campaign_id: str = ""
    region_id: str
    contested_node: str = ""
    attacker_faction_id: str
    defender_faction_id: str
    winning_faction_id: str = ""
    is_stalemate: bool = False
    attacker_casualties: int = 0
    defender_casualties: int = 0
    territory_captured: bool = False
    unrest_delta: int = 0
    narrative: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


@register_event("runefoble.events.watcher.faction_territory_captured")
class FactionTerritoryCapturedEvent(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "RegionalUnrest"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.watcher.faction_territory_captured"
    campaign_id: str = ""
    region_id: str
    previous_controlling_faction_id: str | None = None
    new_controlling_faction_id: str
    territory_node: str
    unrest_delta: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


@register_event("runefoble.events.watcher.regional_unrest_escalated")
class RegionalUnrestEscalatedEvent(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "RegionalUnrest"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.watcher.regional_unrest_escalated"
    campaign_id: str = ""
    region_id: str
    previous_unrest: int = 0
    current_unrest: int = 0
    unrest_delta: int = 0
    alert_level: str = "calm"
    security_level: str = "standard"
    economic_friction: float = 0.0
    cause: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


FactionSkirmishResolved = FactionSkirmishResolvedEvent
FactionTerritoryCaptured = FactionTerritoryCapturedEvent
RegionalUnrestEscalated = RegionalUnrestEscalatedEvent

__all__ = [
    "FactionSkirmishResolvedEvent",
    "FactionSkirmishResolved",
    "FactionTerritoryCapturedEvent",
    "FactionTerritoryCaptured",
    "RegionalUnrestEscalatedEvent",
    "RegionalUnrestEscalated",
]
