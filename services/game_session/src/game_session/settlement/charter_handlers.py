"""Frontier haven chartering and facility upgrade handlers mixin for settlements.

Governed by ADR-0002, ADR-0007, ADR-0011, and Hard Invariant 2.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from eventsource.domain.decorators import handles
from game_session.settlement.models import (
    DEFAULT_FACILITIES,
    FACILITY_REST_BOONS,
    FACILITY_TIER_NAMES,
)
from runefoble_events.settlements import (
    SettlementCharteredEvent,
    SettlementRestBoonClaimedEvent,
    SettlementUpgradedEvent,
)

if TYPE_CHECKING:
    from game_session.settlement.models import SettlementState


def _to_uuid(val: Any) -> UUID:
    try:
        return val if isinstance(val, UUID) else UUID(str(val))
    except Exception:
        return uuid4()


class CharterHandlersMixin:
    """Event handlers and command methods for West Marches frontier haven chartering."""

    _state: SettlementState
    aggregate_id: Any
    create_event: Any

    @handles(SettlementCharteredEvent)
    def handle_chartered(self, ev: SettlementCharteredEvent) -> None:
        """Handle legacy chartering for West Marches persistent frontier."""
        fac = dict(ev.facilities or DEFAULT_FACILITIES)
        cid = [str(ev.founded_by_campaign_id)] if ev.founded_by_campaign_id else []
        s = self._state
        s.settlement_id = ev.settlement_id or str(ev.aggregate_id)
        s.shared_world_id, s.name = ev.shared_world_id, ev.name
        s.settlement_type, s.region = ev.settlement_type, ev.region
        s.coordinates, s.facilities = dict(ev.coordinates), fac
        s.campaign_id, s.chartered_by = str(ev.founded_by_campaign_id), ev.chartered_by
        s.level, s.defense_rating = ev.level, ev.defense_rating
        s.contributing_campaigns, s.is_founded = cid, True
        s.active_boons = {k: FACILITY_REST_BOONS.get(k, "") for k in fac}

    @handles(SettlementUpgradedEvent)
    def handle_upgraded(self, ev: SettlementUpgradedEvent) -> None:
        """Handle facility upgrades."""
        s = self._state
        s.facilities[ev.facility_id] = ev.new_tier
        if ev.facility_id in FACILITY_REST_BOONS:
            s.active_boons[ev.facility_id] = FACILITY_REST_BOONS[ev.facility_id]
        if (cid := str(ev.contributing_campaign_id)) and cid not in s.contributing_campaigns:
            s.contributing_campaigns.append(cid)
        for mat, qty in ev.materials_spent.items():
            s.materials_treasury[mat] = s.materials_treasury.get(mat, 0) + qty
        s.gold_invested += ev.gold_spent
        if ev.facility_id == "fortifications":
            s.defense_rating = max(s.defense_rating, ev.defense_rating)
        s.level = max(1, max(s.facilities.values()))

    @handles(SettlementRestBoonClaimedEvent)
    def handle_boon_claimed(self, ev: SettlementRestBoonClaimedEvent) -> None:
        """Handle claiming of rest boons."""
        self._state.active_boons[ev.facility_id] = ev.boon

    def charter(self, name: str, shared_world_id: str, **kw: Any) -> str:
        """Legacy charter for frontier havens."""
        sid = str(self.aggregate_id or uuid4())
        p = {"shared_world_id": str(shared_world_id), "name": name, "level": 1}
        p |= {"defense_rating": kw.get("defense_rating", 10)}
        p |= {"coordinates": kw.get("coordinates") or {}}
        p |= {"facilities": kw.get("facilities") or dict(DEFAULT_FACILITIES)}
        p |= {"region": kw.get("region", "Wilderness")}
        p |= {"settlement_type": kw.get("settlement_type", "haven")}
        p |= {"metadata": kw.get("metadata") or {}}
        p |= {"founded_by_campaign_id": str(kw.get("founded_by_campaign_id", ""))}
        p |= {"chartered_by": kw.get("chartered_by", "")}
        self.create_event(
            SettlementCharteredEvent, aggregate_id=_to_uuid(sid), settlement_id=sid, **p
        )
        return sid

    charter_haven = charter

    def upgrade_facility(
        self,
        facility_id: str,
        contributing_campaign_id: str = "",
        gold_spent: int = 0,
        materials_spent: dict[str, int] | None = None,
        **kw: Any,
    ) -> int:
        """Upgrade haven facilities."""
        next_tier = self._state.facilities.get(facility_id, 0) + 1
        tier_name = FACILITY_TIER_NAMES.get(facility_id, {}).get(next_tier, f"Tier {next_tier}")
        new_def = self._state.defense_rating + (5 if facility_id == "fortifications" else 0)
        sid = str(self._state.settlement_id or self.aggregate_id)
        p = {"shared_world_id": self._state.shared_world_id, "facility_id": facility_id}
        p |= {"new_tier": next_tier, "tier_name": tier_name, "gold_spent": gold_spent}
        p |= {"contributing_campaign_id": str(contributing_campaign_id), "defense_rating": new_def}
        p |= {"materials_spent": materials_spent or {}, "metadata": kw.get("metadata") or {}}
        self.create_event(
            SettlementUpgradedEvent, aggregate_id=_to_uuid(sid), settlement_id=sid, **p
        )
        return next_tier

    def claim_rest_boon(
        self,
        campaign_id: str,
        character_id: str = "",
        claimed_by: str = "",
        facility_id: str = "sanctum",
        **kw: Any,
    ) -> str:
        """Claim resting boons from settlement sanctum."""
        boon = FACILITY_REST_BOONS.get(
            facility_id, "Restful Refuge: Safe haven from wandering monsters."
        )
        sid = str(self._state.settlement_id or self.aggregate_id)
        p = {"shared_world_id": self._state.shared_world_id, "campaign_id": str(campaign_id)}
        p |= {"character_id": character_id, "claimed_by": claimed_by, "facility_id": facility_id}
        p |= {"boon": boon, "metadata": kw.get("metadata") or {}}
        self.create_event(
            SettlementRestBoonClaimedEvent, aggregate_id=_to_uuid(sid), settlement_id=sid, **p
        )
        return boon
