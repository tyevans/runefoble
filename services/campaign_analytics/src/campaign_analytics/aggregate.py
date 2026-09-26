"""Event-sourced aggregate for Campaign Chronicle and Milestone Archive.

Governed by:
- ADR-0011: eventsource-py Core Event Sourcing
- Hard Invariant 2: Domain state changes flow strictly through DeclarativeAggregate subclasses.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from pydantic import BaseModel, Field
from runefoble_events.analytics import (
    ChronicleMilestoneRecorded,
    CombatTelemetrySnapshotCreated,
    EncounterMvpAwarded,
)


class MilestoneState(BaseModel):
    """Immutable state for a recorded milestone."""

    id: str
    milestone_type: str
    title: str
    description: str
    timestamp: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class MvpAwardState(BaseModel):
    """Immutable state for an MVP award."""

    award_title: str
    combatant_id: str
    combatant_name: str
    metric_name: str
    score: float


class CampaignChronicleState(BaseModel):
    """Reconstituted state for a Campaign Chronicle aggregate."""

    campaign_id: str = ""
    session_id: str = ""
    milestones: list[MilestoneState] = Field(default_factory=list)
    mvp_awards: list[MvpAwardState] = Field(default_factory=list)
    total_damage_logged: int = 0
    total_movements_logged: int = 0


class CampaignChronicleAggregate(DeclarativeAggregate[CampaignChronicleState]):
    """Event-sourced aggregate representing the persistent historical chronicle of a campaign."""

    aggregate_type = "CampaignChronicle"
    requires_creation_event = False

    def __init__(self, aggregate_id: UUID | None = None) -> None:
        super().__init__(aggregate_id=aggregate_id)
        if self._state is None:
            self._state = CampaignChronicleState()

    def record_milestone(
        self,
        campaign_id: str,
        session_id: str,
        milestone_type: str,
        title: str,
        description: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Command to record a new narrative or combat milestone."""
        self.create_event(
            ChronicleMilestoneRecorded,
            campaign_id_str=campaign_id,
            session_id_str=session_id,
            milestone_type=milestone_type,
            title=title,
            description=description,
            metadata=metadata or {},
        )

    def award_mvp(
        self,
        campaign_id: str,
        session_id: str,
        encounter_id: str,
        combatant_id: str,
        combatant_name: str,
        award_title: str,
        metric_name: str,
        score: float,
    ) -> None:
        """Command to confer an encounter or session MVP award."""
        self.create_event(
            EncounterMvpAwarded,
            campaign_id_str=campaign_id,
            session_id_str=session_id,
            encounter_id=encounter_id,
            combatant_id=combatant_id,
            combatant_name=combatant_name,
            award_title=award_title,
            metric_name=metric_name,
            score=score,
        )

    def record_snapshot(
        self,
        campaign_id: str,
        session_id: str,
        total_damage: int,
        total_movements: int,
        active_combatants: int,
    ) -> None:
        """Command to snapshot aggregated telemetry."""
        self.create_event(
            CombatTelemetrySnapshotCreated,
            campaign_id_str=campaign_id,
            session_id_str=session_id,
            total_damage=total_damage,
            total_movements=total_movements,
            active_combatants=active_combatants,
        )

    @handles(ChronicleMilestoneRecorded)
    def handle_milestone_recorded(self, event: ChronicleMilestoneRecorded) -> None:
        self.state.campaign_id = event.campaign_id_str or self.state.campaign_id
        self.state.session_id = event.session_id_str or self.state.session_id
        self.state.milestones.append(
            MilestoneState(
                id=str(event.event_id),
                milestone_type=event.milestone_type,
                title=event.title,
                description=event.description,
                timestamp=event.occurred_at.isoformat(),
                metadata=event.metadata,
            )
        )

    @handles(EncounterMvpAwarded)
    def handle_mvp_awarded(self, event: EncounterMvpAwarded) -> None:
        self.state.campaign_id = event.campaign_id_str or self.state.campaign_id
        self.state.session_id = event.session_id_str or self.state.session_id
        self.state.mvp_awards.append(
            MvpAwardState(
                award_title=event.award_title,
                combatant_id=event.combatant_id,
                combatant_name=event.combatant_name,
                metric_name=event.metric_name,
                score=event.score,
            )
        )

    @handles(CombatTelemetrySnapshotCreated)
    def handle_snapshot_created(self, event: CombatTelemetrySnapshotCreated) -> None:
        self.state.campaign_id = event.campaign_id_str or self.state.campaign_id
        self.state.session_id = event.session_id_str or self.state.session_id
        self.state.total_damage_logged += event.total_damage
        self.state.total_movements_logged += event.total_movements
