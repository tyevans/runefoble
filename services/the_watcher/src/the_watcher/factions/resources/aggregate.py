"""Event-sourced FactionResourceAggregate for treasury, mercenaries, and bribery."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from runefoble_events.faction_resources import (
    FactionBriberyAttemptedEvent,
    FactionMercenaryRecruitedEvent,
    FactionResourceUpdatedEvent,
)
from the_watcher.factions.resources.bribery import calculate_bribery_outcome
from the_watcher.factions.resources.models import FactionResourceState, MercenaryUnit


class FactionResourceAggregate(DeclarativeAggregate[FactionResourceState]):
    """Aggregate managing a faction's treasury, contraband, mercenary payroll, and bribery."""

    aggregate_type = "FactionResource"

    def __init__(self, aggregate_id: UUID | None = None, **kwargs: Any) -> None:
        super().__init__(aggregate_id=aggregate_id, **kwargs)
        if self._state is None:
            self._state = FactionResourceState(faction_id=str(aggregate_id or uuid4()))

    def _create(self, event_cls: Any, camp: str = "", **kwargs: Any) -> None:
        self.create_event(
            event_cls,
            aggregate_id=self.aggregate_id,
            faction_id=self.state.faction_id,
            campaign_id=camp or self.state.campaign_id,
            **kwargs,
        )

    @handles(FactionResourceUpdatedEvent)
    def _on_resources_updated(self, event: FactionResourceUpdatedEvent) -> None:
        self.state.treasury = event.treasury
        self.state.contraband_score = event.contraband
        if event.campaign_id:
            self.state.campaign_id = event.campaign_id
        self.state.history.append({"type": "adjust", "d_treasury": event.delta_treasury})

    @handles(FactionMercenaryRecruitedEvent)
    def _on_mercenary_recruited(self, event: FactionMercenaryRecruitedEvent) -> None:
        self.state.treasury = max(0, self.state.treasury - event.cost)
        self.state.total_mercenaries = event.total_mercenaries
        if event.campaign_id:
            self.state.campaign_id = event.campaign_id
        u = MercenaryUnit(
            name=event.unit_name, count=event.count, upkeep_per_tick=event.upkeep_per_tick
        )
        self.state.mercenaries.append(u)
        self.state.history.append({"type": "recruit", "unit": event.unit_name})

    @handles(FactionBriberyAttemptedEvent)
    def _on_bribery_attempted(self, event: FactionBriberyAttemptedEvent) -> None:
        self.state.treasury = event.remaining_treasury
        if event.campaign_id:
            self.state.campaign_id = event.campaign_id
        self.state.history.append({"type": "bribery", "target": event.target_name})

    def adjust_resources(
        self,
        treasury_delta: int = 0,
        contraband_delta: int = 0,
        reason: str = "",
        campaign_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._create(
            FactionResourceUpdatedEvent,
            camp=campaign_id,
            treasury=max(0, self.state.treasury + treasury_delta),
            contraband=max(0, self.state.contraband_score + contraband_delta),
            mercenaries_count=self.state.total_mercenaries,
            delta_treasury=treasury_delta,
            delta_contraband=contraband_delta,
            reason=reason,
            metadata=metadata or {},
        )

    def apply_upkeep(self, campaign_id: str = "") -> int:
        upkeep = sum(u.count * u.upkeep_per_tick for u in self.state.mercenaries)
        if upkeep > 0:
            self.adjust_resources(-upkeep, reason="mercenary_upkeep", campaign_id=campaign_id)
        return upkeep

    def recruit_mercenaries(
        self,
        unit_name: str,
        count: int = 1,
        cost_per_unit: int = 10,
        unit_type: str = "infantry",
        upkeep_per_tick: int = 1,
        campaign_id: str = "",
    ) -> None:
        cost = count * cost_per_unit
        if self.state.treasury < cost:
            raise ValueError(f"Insufficient treasury ({self.state.treasury}) for cost ({cost})")
        self._create(
            FactionMercenaryRecruitedEvent,
            camp=campaign_id,
            unit_name=unit_name,
            count=count,
            cost=cost,
            unit_type=unit_type,
            total_mercenaries=self.state.total_mercenaries + count,
            upkeep_per_tick=upkeep_per_tick,
        )

    def execute_bribery(
        self,
        target_name: str,
        target_role: str,
        bribe: int,
        loyalty: str,
        counter: int,
        roll: int | None,
        camp_id: str = "",
    ) -> dict[str, Any]:
        if self.state.treasury < bribe:
            raise ValueError(f"Insufficient treasury ({self.state.treasury}) for bribe ({bribe})")
        res = calculate_bribery_outcome(target_name, target_role, bribe, loyalty, counter, roll)
        rem = self.state.treasury - bribe
        keys = ("dc", "roll", "modifier", "success", "outcome", "narrative")
        self._create(
            FactionBriberyAttemptedEvent,
            camp=camp_id,
            target_name=target_name,
            bribe_amount=bribe,
            counter_bribe=counter,
            remaining_treasury=rem,
            **{k: res[k] for k in keys},
        )
        res["remaining_treasury"] = rem
        return res
