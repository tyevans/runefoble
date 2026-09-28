"""Event-sourced Settlement Aggregate managing civic scales, districts, and haven charters.

Governed by ADR-0002, ADR-0007, ADR-0011, and Hard Invariant 2.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from game_session.settlement.bulletin_handlers import BulletinHandlersMixin
from game_session.settlement.charter_handlers import CharterHandlersMixin
from game_session.settlement.models import (
    DEFAULT_TIER_DISTRICTS,
    SCALE_MAX_DISTRICTS,
    SCALE_TO_TIER,
    TIER_MIN_PROSPERITY,
    TIER_TO_SCALE,
    SettlementScale,
    SettlementState,
)
from runefoble_events.settlements import (
    SettlementFoundedEvent,
    SettlementTierUpgradedEvent,
)


def _to_uuid(val: Any) -> UUID:
    try:
        return val if isinstance(val, UUID) else UUID(str(val))
    except Exception:
        return uuid4()


class SettlementAggregate(
    BulletinHandlersMixin, CharterHandlersMixin, DeclarativeAggregate[SettlementState]
):
    """Event-sourced aggregate managing settlement layout, scaling, and havens."""

    aggregate_type = "Settlement"
    requires_creation_event = False

    def __init__(self, aggregate_id: Any = None, **kwargs: Any) -> None:
        super().__init__(aggregate_id=aggregate_id, **kwargs)
        if self._state is None:
            self._state = SettlementState(settlement_id=str(aggregate_id or ""))

    @handles(SettlementFoundedEvent)
    def handle_settlement_founded(self, ev: SettlementFoundedEvent) -> None:
        """Handle founding of a settlement haven."""
        scale_key = ev.scale.lower()
        tier = ev.tier or SCALE_TO_TIER.get(scale_key, 1)
        max_districts = SCALE_MAX_DISTRICTS.get(tier, 2)
        districts = list(ev.unlocked_districts or DEFAULT_TIER_DISTRICTS.get(tier, []))
        s = self._state
        s.settlement_id = ev.settlement_id or str(ev.aggregate_id)
        s.campaign_id, s.name, s.scale = str(ev.campaign_id), ev.name, scale_key
        s.tier, s.biome, s.coordinates = tier, ev.biome, dict(ev.coordinates)
        s.prosperity = max(s.prosperity, ev.prosperity)
        s.max_districts, s.districts = max_districts, districts[:max_districts]
        s.chartered_by, s.is_founded = ev.founded_by, True

    @handles(SettlementTierUpgradedEvent)
    def handle_tier_upgraded(self, ev: SettlementTierUpgradedEvent) -> None:
        """Handle settlement advancement to higher civic scale tier."""
        s = self._state
        s.tier = int(ev.new_tier)
        s.scale = ev.scale or TIER_TO_SCALE.get(s.tier, s.scale)
        s.max_districts = SCALE_MAX_DISTRICTS.get(s.tier, 32)
        if ev.prosperity:
            s.prosperity = max(s.prosperity, ev.prosperity)
        for d in ev.unlocked_districts:
            if d not in s.districts and len(s.districts) < s.max_districts:
                s.districts.append(d)

    def found(
        self,
        name: str,
        campaign_id: str,
        scale: str = SettlementScale.VILLAGE.value,
        biome: str = "river_confluence",
        coordinates: dict[str, float] | None = None,
        prosperity: int = 0,
        districts: list[str] | None = None,
        founded_by: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Found a new settlement haven with scale, biome, and initial zoning districts."""
        if self._state.is_founded:
            raise ValueError(f"Settlement '{self.aggregate_id}' has already been founded")

        if (scale_key := scale.lower()) not in SCALE_TO_TIER:
            valid = ", ".join(SCALE_TO_TIER.keys())
            raise ValueError(f"Invalid settlement scale '{scale}'. Must be one of: {valid}")

        tier = SCALE_TO_TIER[scale_key]
        max_districts = SCALE_MAX_DISTRICTS.get(tier, 2)
        if districts is not None and len(districts) > max_districts:
            raise ValueError(
                f"Scale '{scale}' permits at most {max_districts} districts, but {len(districts)} were specified"
            )
        initial_districts = list(
            districts if districts is not None else DEFAULT_TIER_DISTRICTS.get(tier, [])
        )[:max_districts]

        sid = str(self.aggregate_id or uuid4())
        p = {"campaign_id": str(campaign_id), "name": name, "scale": scale_key, "tier": tier}
        p |= {"biome": biome, "coordinates": coordinates or {}, "prosperity": prosperity}
        p |= {"unlocked_districts": initial_districts, "founded_by": founded_by}
        p |= {"metadata": metadata or {}}
        self.create_event(
            SettlementFoundedEvent, aggregate_id=_to_uuid(sid), settlement_id=sid, **p
        )
        return sid

    def upgrade_tier(
        self,
        new_tier: int | None = None,
        target_scale: str | None = None,
        prosperity: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Advance settlement scale tier if prerequisites are met."""
        if not self._state.is_founded:
            raise ValueError(f"Settlement '{self.aggregate_id}' has not been founded yet")

        if new_tier is None:
            new_tier = (
                SCALE_TO_TIER.get(target_scale.lower()) if target_scale else self._state.tier + 1
            )

        expected_tier = self._state.tier + 1
        if new_tier != expected_tier:
            raise ValueError(
                f"Invalid tier upgrade: current tier is {self._state.tier}, can only advance to tier {expected_tier}"
            )

        if new_tier not in TIER_TO_SCALE:
            raise ValueError(
                f"Tier {new_tier} exceeds maximum settlement scale (Tier 5 - Metropolis)"
            )

        eff_pros = self._state.prosperity if prosperity is None else prosperity
        min_prosperity = TIER_MIN_PROSPERITY.get(new_tier, 0)
        if eff_pros < min_prosperity:
            raise ValueError(
                f"Insufficient civic prosperity: {eff_pros} < required {min_prosperity} for tier {new_tier}"
            )

        unlocked = DEFAULT_TIER_DISTRICTS.get(new_tier, [])
        sid = str(self._state.settlement_id or self.aggregate_id)
        p = {"old_tier": self._state.tier, "new_tier": new_tier, "unlocked_districts": unlocked}
        p |= {"scale": TIER_TO_SCALE[new_tier], "prosperity": eff_pros, "metadata": metadata or {}}
        self.create_event(
            SettlementTierUpgradedEvent, aggregate_id=_to_uuid(sid), settlement_id=sid, **p
        )
        return new_tier
