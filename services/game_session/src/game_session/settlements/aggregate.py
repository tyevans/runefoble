"""Event-sourced Settlement Aggregate managing multi-campaign havens and facilities.

Governed by ADR-0007, ADR-0011, and Hard Invariant 2.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from game_session.settlements.models import (
    DEFAULT_FACILITIES,
    FACILITY_REST_BOONS,
    FACILITY_TIER_NAMES,
    SettlementState,
)
from runefoble_events.settlements import (
    SettlementCharteredEvent,
    SettlementRestBoonClaimedEvent,
    SettlementUpgradedEvent,
)


def _to_uuid(val: Any) -> UUID:
    try:
        return val if isinstance(val, UUID) else UUID(str(val))
    except Exception:
        return uuid4()


class SettlementAggregate(DeclarativeAggregate[SettlementState]):
    """Event-sourced aggregate managing frontier settlements, havens, and workshops."""

    aggregate_type = "Settlement"
    requires_creation_event = False

    def __init__(self, aggregate_id: Any = None, **kwargs: Any) -> None:
        super().__init__(aggregate_id=aggregate_id, **kwargs)
        if self._state is None:
            self._state = SettlementState(settlement_id=str(aggregate_id or ""))

    @handles(SettlementCharteredEvent)
    def handle_chartered(self, ev: SettlementCharteredEvent) -> None:
        fac = dict(ev.facilities) if ev.facilities else dict(DEFAULT_FACILITIES)
        cid = [str(ev.founded_by_campaign_id)] if ev.founded_by_campaign_id else []
        self._state = SettlementState(
            settlement_id=ev.settlement_id or str(ev.aggregate_id),
            shared_world_id=ev.shared_world_id,
            name=ev.name,
            settlement_type=ev.settlement_type,
            region=ev.region,
            coordinates=dict(ev.coordinates),
            founded_by_campaign_id=str(ev.founded_by_campaign_id),
            chartered_by=ev.chartered_by,
            level=ev.level,
            defense_rating=ev.defense_rating,
            facilities=fac,
            contributing_campaigns=cid,
            active_boons={k: FACILITY_REST_BOONS.get(k, "") for k in fac},
        )

    @handles(SettlementUpgradedEvent)
    def handle_upgraded(self, event: SettlementUpgradedEvent) -> None:
        self.state.facilities[event.facility_id] = event.new_tier
        if event.facility_id in FACILITY_REST_BOONS:
            self.state.active_boons[event.facility_id] = FACILITY_REST_BOONS[event.facility_id]
        cid = str(event.contributing_campaign_id)
        if cid and cid not in self.state.contributing_campaigns:
            self.state.contributing_campaigns.append(cid)
        for mat, qty in event.materials_spent.items():
            self.state.materials_treasury[mat] = self.state.materials_treasury.get(mat, 0) + qty
        self.state.gold_invested += event.gold_spent
        if event.facility_id == "fortifications":
            self.state.defense_rating = max(self.state.defense_rating, event.defense_rating)
        self.state.level = max(1, max(self.state.facilities.values()))

    @handles(SettlementRestBoonClaimedEvent)
    def handle_boon_claimed(self, event: SettlementRestBoonClaimedEvent) -> None:
        self.state.active_boons[event.facility_id] = event.boon

    def charter(self, name: str, shared_world_id: str, **kw: Any) -> str:
        sid = str(self.aggregate_id or uuid4())
        self.create_event(
            SettlementCharteredEvent,
            aggregate_id=_to_uuid(sid),
            settlement_id=sid,
            shared_world_id=str(shared_world_id),
            name=name,
            settlement_type=kw.get("settlement_type", "outpost"),
            region=kw.get("region", "Wilderness"),
            coordinates=kw.get("coordinates") or {},
            founded_by_campaign_id=str(kw.get("founded_by_campaign_id", "")),
            chartered_by=kw.get("chartered_by", ""),
            level=1,
            defense_rating=kw.get("defense_rating", 10),
            facilities=kw.get("facilities") or dict(DEFAULT_FACILITIES),
            metadata=kw.get("metadata") or {},
        )
        return sid

    def upgrade_facility(
        self,
        facility_id: str,
        contributing_campaign_id: str = "",
        gold_spent: int = 0,
        materials_spent: dict[str, int] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        next_tier = self.state.facilities.get(facility_id, 0) + 1
        tier_name = FACILITY_TIER_NAMES.get(facility_id, {}).get(next_tier, f"Tier {next_tier}")
        new_def = self.state.defense_rating + (5 if facility_id == "fortifications" else 0)
        sid = str(self.state.settlement_id or self.aggregate_id)
        self.create_event(
            SettlementUpgradedEvent,
            aggregate_id=_to_uuid(sid),
            settlement_id=sid,
            shared_world_id=self.state.shared_world_id,
            facility_id=facility_id,
            new_tier=next_tier,
            tier_name=tier_name,
            contributing_campaign_id=str(contributing_campaign_id),
            gold_spent=gold_spent,
            materials_spent=materials_spent or {},
            defense_rating=new_def,
            metadata=metadata or {},
        )
        return next_tier

    def claim_rest_boon(
        self,
        campaign_id: str,
        character_id: str = "",
        claimed_by: str = "",
        facility_id: str = "sanctum",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        boon = FACILITY_REST_BOONS.get(
            facility_id, "Restful Refuge: Safe haven from wandering monsters."
        )
        sid = str(self.state.settlement_id or self.aggregate_id)
        self.create_event(
            SettlementRestBoonClaimedEvent,
            aggregate_id=_to_uuid(sid),
            settlement_id=sid,
            shared_world_id=self.state.shared_world_id,
            campaign_id=str(campaign_id),
            character_id=character_id,
            claimed_by=claimed_by,
            facility_id=facility_id,
            boon=boon,
            metadata=metadata or {},
        )
        return boon
