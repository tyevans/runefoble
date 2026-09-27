"""Event-sourced RegionalUnrestAggregate for territory control and regional unrest tracking."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from runefoble_events.turf_war import (
    FactionSkirmishResolvedEvent,
    FactionTerritoryCapturedEvent,
    RegionalUnrestEscalatedEvent,
)
from the_watcher.turf_war.models import RegionalUnrestState


class RegionalUnrestAggregate(DeclarativeAggregate[RegionalUnrestState]):
    """Aggregate managing regional unrest metrics, security levels, and territorial ownership."""

    aggregate_type = "RegionalUnrest"

    def __init__(self, aggregate_id: UUID | None = None, **kwargs: Any) -> None:
        super().__init__(aggregate_id=aggregate_id, **kwargs)
        if self._state is None:
            self._state = RegionalUnrestState(region_id=str(aggregate_id or uuid4()))

    def _create(self, event_cls: Any, **kwargs: Any) -> None:
        self.create_event(
            event_cls,
            aggregate_id=self.aggregate_id,
            region_id=self.state.region_id,
            campaign_id=self.state.campaign_id,
            **kwargs,
        )

    @handles(FactionSkirmishResolvedEvent)
    def _on_skirmish_resolved(self, event: FactionSkirmishResolvedEvent) -> None:
        if event.campaign_id:
            self.state.campaign_id = event.campaign_id
        if event.contested_node and event.contested_node not in self.state.contested_nodes:
            self.state.contested_nodes.append(event.contested_node)
        self.state.recent_skirmishes.append(
            {
                "skirmish_id": event.skirmish_id,
                "winner": event.winning_faction_id,
                "contested_node": event.contested_node,
                "territory_captured": event.territory_captured,
                "casualties": event.attacker_casualties + event.defender_casualties,
                "narrative": event.narrative,
            }
        )
        if len(self.state.recent_skirmishes) > 20:
            self.state.recent_skirmishes.pop(0)

    @handles(FactionTerritoryCapturedEvent)
    def _on_territory_captured(self, event: FactionTerritoryCapturedEvent) -> None:
        if event.campaign_id:
            self.state.campaign_id = event.campaign_id
        self.state.controlling_faction_id = event.new_controlling_faction_id
        if event.territory_node and event.territory_node not in self.state.contested_nodes:
            self.state.contested_nodes.append(event.territory_node)

    @handles(RegionalUnrestEscalatedEvent)
    def _on_unrest_escalated(self, event: RegionalUnrestEscalatedEvent) -> None:
        if event.campaign_id:
            self.state.campaign_id = event.campaign_id
        self.state.unrest_score = event.current_unrest
        self.state.alert_level = event.alert_level
        self.state.security_level = event.security_level
        self.state.economic_friction = event.economic_friction

    def record_skirmish(
        self,
        skirmish_id: str,
        attacker_faction_id: str,
        defender_faction_id: str,
        winning_faction_id: str,
        contested_node: str,
        attacker_casualties: int,
        defender_casualties: int,
        territory_captured: bool,
        unrest_delta: int,
        narrative: str,
        is_stalemate: bool = False,
        campaign_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Create and apply a FactionSkirmishResolvedEvent."""
        if campaign_id:
            self.state.campaign_id = campaign_id
        self._create(
            FactionSkirmishResolvedEvent,
            skirmish_id=skirmish_id,
            attacker_faction_id=attacker_faction_id,
            defender_faction_id=defender_faction_id,
            winning_faction_id=winning_faction_id,
            contested_node=contested_node,
            attacker_casualties=attacker_casualties,
            defender_casualties=defender_casualties,
            territory_captured=territory_captured,
            unrest_delta=unrest_delta,
            narrative=narrative,
            is_stalemate=is_stalemate,
            metadata=metadata or {},
        )

    def capture_territory(
        self,
        new_controlling_faction_id: str,
        territory_node: str,
        unrest_delta: int = 0,
        campaign_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Create and apply a FactionTerritoryCapturedEvent."""
        if campaign_id:
            self.state.campaign_id = campaign_id
        prev_owner = self.state.controlling_faction_id
        self._create(
            FactionTerritoryCapturedEvent,
            previous_controlling_faction_id=prev_owner,
            new_controlling_faction_id=new_controlling_faction_id,
            territory_node=territory_node,
            unrest_delta=unrest_delta,
            metadata=metadata or {},
        )

    def escalate_unrest(
        self,
        current_unrest: int,
        unrest_delta: int,
        alert_level: str,
        security_level: str,
        economic_friction: float,
        cause: str = "",
        campaign_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Create and apply a RegionalUnrestEscalatedEvent."""
        if campaign_id:
            self.state.campaign_id = campaign_id
        prev_score = self.state.unrest_score
        self._create(
            RegionalUnrestEscalatedEvent,
            previous_unrest=prev_score,
            current_unrest=current_unrest,
            unrest_delta=unrest_delta,
            alert_level=alert_level,
            security_level=security_level,
            economic_friction=economic_friction,
            cause=cause,
            metadata=metadata or {},
        )
