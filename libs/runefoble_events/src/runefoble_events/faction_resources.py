"""Domain events for NPC faction economic resources, mercenary upkeep, and bribery."""

from __future__ import annotations

from typing import Any, ClassVar
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event("runefoble.events.watcher.faction_resource_updated")
class FactionResourceUpdatedEvent(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "FactionResource"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.watcher.faction_resource_updated"
    faction_id: str
    campaign_id: str = ""
    treasury: int = 0
    contraband: int = 0
    mercenaries_count: int = 0
    delta_treasury: int = 0
    delta_contraband: int = 0
    reason: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


@register_event("runefoble.events.watcher.faction_mercenary_recruited")
class FactionMercenaryRecruitedEvent(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "FactionResource"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.watcher.faction_mercenary_recruited"
    faction_id: str
    campaign_id: str = ""
    unit_name: str
    count: int = 1
    cost: int = 0
    unit_type: str = "infantry"
    total_mercenaries: int = 0
    upkeep_per_tick: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)


@register_event("runefoble.events.watcher.faction_bribery_attempted")
class FactionBriberyAttemptedEvent(BaseRunefobleEvent):
    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "FactionResource"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.watcher.faction_bribery_attempted"
    faction_id: str
    campaign_id: str = ""
    target_name: str
    bribe_amount: int
    dc: int
    roll: int
    modifier: int = 0
    counter_bribe: int = 0
    success: bool = False
    outcome: str = "failure"
    narrative: str = ""
    remaining_treasury: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


FactionResourceUpdated = FactionResourceUpdatedEvent
FactionMercenaryRecruited = FactionMercenaryRecruitedEvent
FactionBriberyAttempted = FactionBriberyAttemptedEvent

__all__ = [
    "FactionResourceUpdatedEvent",
    "FactionResourceUpdated",
    "FactionMercenaryRecruitedEvent",
    "FactionMercenaryRecruited",
    "FactionBriberyAttemptedEvent",
    "FactionBriberyAttempted",
]
