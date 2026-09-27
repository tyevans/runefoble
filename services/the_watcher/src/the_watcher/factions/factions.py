"""Event-sourced FactionAggregate using eventsource-py.

Governed by:
- ADR-0002: Event-Driven Watcher Gameplay Orchestration
- ADR-0011: eventsource-py Core Event Sourcing
- Hard Invariant 2: Domain state changes flow strictly through DeclarativeAggregate subclasses.
"""

from __future__ import annotations

from typing import Any

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from pydantic import BaseModel, Field
from runefoble_events.watcher import (
    FactionAgendaAdvanced,
    FactionAgendaSet,
    FactionCreated,
    GeopoliticalShiftOccurred,
)


class FactionState(BaseModel):
    """Internal state representation for an NPC faction in the campaign world."""

    faction_id: str
    campaign_id: str
    name: str
    influence: int = 50
    resources: int = 50
    disposition: str = "neutral"
    active_goal: str = ""
    goal_progress: int = 0
    goal_target: int = 100
    rival_faction_ids: list[str] = Field(default_factory=list)
    territory: str = ""
    history: list[dict[str, Any]] = Field(default_factory=list)
    shifts: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class FactionAggregate(DeclarativeAggregate[FactionState]):
    """Event-sourced aggregate managing faction assets, goals, and geopolitical relationships."""

    aggregate_type = "Faction"
    requires_creation_event = True

    def initialize(
        self,
        campaign_id: str,
        faction_id: str,
        name: str,
        influence: int = 50,
        resources: int = 50,
        disposition: str = "neutral",
        active_goal: str = "",
        rival_faction_ids: list[str] | None = None,
        territory: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Initialize a new autonomous faction within a campaign."""
        self.create_event(
            FactionCreated,
            aggregate_id=self.aggregate_id,
            campaign_id=campaign_id,
            faction_id=faction_id,
            name=name,
            influence=max(1, min(100, influence)),
            resources=max(0, resources),
            disposition=disposition,
            active_goal=active_goal,
            rival_faction_ids=rival_faction_ids or [],
            territory=territory,
            metadata=metadata or {},
        )

    def set_agenda(
        self,
        active_goal: str,
        target_progress: int = 100,
        target_faction_or_location: str | None = None,
    ) -> None:
        """Assign or update a faction's active agenda goal."""
        self.create_event(
            FactionAgendaSet,
            aggregate_id=self.aggregate_id,
            campaign_id=self.state.campaign_id,
            faction_id=self.state.faction_id,
            active_goal=active_goal,
            target_progress=target_progress,
            current_progress=0,
            target_faction_or_location=target_faction_or_location,
        )

    def advance_agenda(
        self,
        agenda_name: str,
        roll: int,
        modifier: int,
        dc: int,
        outcome: str,
        progress_delta: int,
        narrative: str,
    ) -> None:
        """Advance faction progress toward their active goal based on simulation checks."""
        target = self.state.goal_target if self.state.goal_target > 0 else 100
        new_progress = max(0, min(target, self.state.goal_progress + progress_delta))
        self.create_event(
            FactionAgendaAdvanced,
            aggregate_id=self.aggregate_id,
            campaign_id=self.state.campaign_id,
            faction_id=self.state.faction_id,
            faction_name=self.state.name,
            agenda_name=agenda_name,
            roll=roll,
            modifier=modifier,
            dc=dc,
            outcome=outcome,
            progress_delta=progress_delta,
            current_progress=new_progress,
            target_progress=target,
            narrative=narrative,
        )

    def record_shift(
        self,
        territory: str,
        shift_type: str,
        description: str,
        severity: str = "moderate",
        ripple_effects: list[str] | None = None,
    ) -> None:
        """Record a dynamic geopolitical shift or territorial occupation."""
        self.create_event(
            GeopoliticalShiftOccurred,
            aggregate_id=self.aggregate_id,
            campaign_id=self.state.campaign_id,
            faction_id=self.state.faction_id,
            territory=territory,
            shift_type=shift_type,
            description=description,
            severity=severity,
            ripple_effects=ripple_effects or [],
        )

    # -----------------------------------------------------------------------
    # Event Handlers (@handles)
    # -----------------------------------------------------------------------

    @handles(FactionCreated)
    def _on_created(self, event: FactionCreated) -> None:
        self._state = FactionState(
            faction_id=event.faction_id,
            campaign_id=event.campaign_id,
            name=event.name,
            influence=event.influence,
            resources=event.resources,
            disposition=event.disposition,
            active_goal=event.active_goal,
            goal_progress=0,
            goal_target=100,
            rival_faction_ids=list(event.rival_faction_ids),
            territory=event.territory,
            history=[],
            shifts=[],
            metadata=dict(event.metadata),
        )

    @handles(FactionAgendaSet)
    def _on_agenda_set(self, event: FactionAgendaSet) -> None:
        self.state.active_goal = event.active_goal
        self.state.goal_target = event.target_progress
        self.state.goal_progress = event.current_progress

    @handles(FactionAgendaAdvanced)
    def _on_agenda_advanced(self, event: FactionAgendaAdvanced) -> None:
        self.state.goal_progress = event.current_progress
        if event.outcome in ("success", "critical_success"):
            self.state.influence = min(100, self.state.influence + 2)
            self.state.resources = max(0, self.state.resources + 1)
        elif event.outcome == "countered":
            self.state.influence = max(1, self.state.influence - 1)
            self.state.resources = max(0, self.state.resources - 2)
        elif event.outcome == "failure":
            self.state.resources = max(0, self.state.resources - 1)

        self.state.history.append(
            {
                "agenda": event.agenda_name,
                "roll": event.roll,
                "modifier": event.modifier,
                "dc": event.dc,
                "outcome": event.outcome,
                "progress_delta": event.progress_delta,
                "progress": event.current_progress,
                "narrative": event.narrative,
            }
        )

    @handles(GeopoliticalShiftOccurred)
    def _on_shift_occurred(self, event: GeopoliticalShiftOccurred) -> None:
        if event.territory:
            self.state.territory = event.territory
        self.state.shifts.append(
            {
                "territory": event.territory,
                "shift_type": event.shift_type,
                "description": event.description,
                "severity": event.severity,
                "ripple_effects": list(event.ripple_effects),
            }
        )
