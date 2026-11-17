"""Event-sourced CampaignWorldAggregate: world tick counter, faction registry, latest tick.

Governed by:
- ADR-0011: eventsource-py Core Event Sourcing
- Hard Invariant 2: Domain state changes flow strictly through DeclarativeAggregate subclasses.

One aggregate exists per campaign. It owns the tick counter and the list of faction IDs that
the world simulation advances. Restarting the service rebuilds both from the event store.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from pydantic import BaseModel, Field
from runefoble_events.watcher import CampaignFactionRegistered, WorldTickExecuted


class LatestWorldTick(BaseModel):
    """The most recent executed world tick, rebuilt from WorldTickExecuted events."""

    tick_number: int
    intelligence_bulletin: str
    factions_simulated: list[str] = Field(default_factory=list)
    shifts: list[dict[str, Any]] = Field(default_factory=list)
    rumors: list[str] = Field(default_factory=list)
    timestamp: str


class CampaignWorldState(BaseModel):
    """Durable world simulation state for one campaign."""

    campaign_id: str = ""
    tick_count: int = 0
    faction_ids: list[str] = Field(default_factory=list)
    latest_tick: LatestWorldTick | None = None


class CampaignWorldAggregate(DeclarativeAggregate[CampaignWorldState]):
    """Event-sourced world state: tick counter, faction registry, and latest bulletin."""

    aggregate_type = "CampaignWorld"

    def __init__(self, aggregate_id: UUID) -> None:
        super().__init__(aggregate_id)
        self._state = CampaignWorldState()

    def register_faction(self, campaign_id: str, faction_id: str) -> None:
        """Add a faction to the campaign registry. Registering twice is a no-op."""
        if faction_id in self.state.faction_ids:
            return
        self.create_event(
            CampaignFactionRegistered,
            aggregate_id=self.aggregate_id,
            campaign_id=campaign_id,
            faction_id=faction_id,
        )

    def record_world_tick(
        self,
        campaign_id: str,
        tick_number: int,
        intelligence_bulletin: str,
        factions_simulated: list[str],
        shifts: list[dict[str, Any]],
        rumors: list[str],
    ) -> WorldTickExecuted:
        """Record an executed world tick. The tick number must advance the counter."""
        if tick_number <= self.state.tick_count:
            raise ValueError(
                f"World tick {tick_number} does not advance tick count {self.state.tick_count}."
            )
        return self.create_event(
            WorldTickExecuted,
            aggregate_id=self.aggregate_id,
            campaign_id=campaign_id,
            tick_number=tick_number,
            intelligence_bulletin=intelligence_bulletin,
            factions_simulated=factions_simulated,
            shifts=shifts,
            rumors=rumors,
        )

    # -----------------------------------------------------------------------
    # Event Handlers (@handles)
    # -----------------------------------------------------------------------

    @handles(CampaignFactionRegistered)
    def _on_faction_registered(self, event: CampaignFactionRegistered) -> None:
        self.state.campaign_id = event.campaign_id
        self.state.faction_ids.append(event.faction_id)

    @handles(WorldTickExecuted)
    def _on_world_tick_executed(self, event: WorldTickExecuted) -> None:
        self.state.campaign_id = event.campaign_id
        self.state.tick_count = event.tick_number
        self.state.latest_tick = LatestWorldTick(
            tick_number=event.tick_number,
            intelligence_bulletin=event.intelligence_bulletin,
            factions_simulated=list(event.factions_simulated),
            shifts=list(event.shifts),
            rumors=list(event.rumors),
            timestamp=event.occurred_at.isoformat(),
        )
