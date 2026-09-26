"""Campaign Analytics and Chronicle Archive domain events."""

from __future__ import annotations

from typing import Any, ClassVar
from uuid import UUID, uuid4

from pydantic import Field

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event("runefoble.events.analytics.milestone_recorded")
class ChronicleMilestoneRecorded(BaseRunefobleEvent):
    """Domain event emitted when a campaign milestone is recorded in the chronicle."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "CampaignChronicle"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.analytics.milestone_recorded"
    campaign_id_str: str = ""
    session_id_str: str = ""
    milestone_type: str
    title: str
    description: str
    metadata: dict[str, Any] = Field(default_factory=dict)


@register_event("runefoble.events.analytics.telemetry_snapshot_created")
class CombatTelemetrySnapshotCreated(BaseRunefobleEvent):
    """Domain event emitted when a telemetry aggregate snapshot is calculated."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "CampaignChronicle"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.analytics.telemetry_snapshot_created"
    campaign_id_str: str = ""
    session_id_str: str = ""
    total_damage: int = 0
    total_movements: int = 0
    active_combatants: int = 0


@register_event("runefoble.events.analytics.mvp_awarded")
class EncounterMvpAwarded(BaseRunefobleEvent):
    """Domain event emitted when an encounter or session MVP award is conferred."""

    suppress_event_type_warning: ClassVar[bool] = True
    aggregate_type: str = "CampaignChronicle"
    aggregate_id: UUID = Field(default_factory=uuid4)
    event_type: str = "runefoble.events.analytics.mvp_awarded"
    campaign_id_str: str = ""
    session_id_str: str = ""
    encounter_id: str = "default"
    combatant_id: str
    combatant_name: str
    award_title: str
    metric_name: str
    score: float = 0.0
