"""Event-sourced Establishment Aggregate managing business capacity, operating costs, and amenities.

Governed by ADR-0002, ADR-0007, ADR-0011, and Hard Invariant 2.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from game_session.settlement.models import (
    EstablishmentCategory,
    EstablishmentState,
)
from runefoble_events.settlements import (
    EstablishmentConstructedEvent,
    EstablishmentUpgradedEvent,
)


def _to_uuid(val: Any) -> UUID:
    try:
        return val if isinstance(val, UUID) else UUID(str(val))
    except Exception:
        return uuid4()


class EstablishmentAggregate(DeclarativeAggregate[EstablishmentState]):
    """Event-sourced aggregate managing commercial, civic, and hospitality storefronts."""

    aggregate_type = "Establishment"
    requires_creation_event = False

    def __init__(self, aggregate_id: Any = None, **kwargs: Any) -> None:
        super().__init__(aggregate_id=aggregate_id, **kwargs)
        if self._state is None:
            self._state = EstablishmentState(establishment_id=str(aggregate_id or ""))

    @handles(EstablishmentConstructedEvent)
    def handle_constructed(self, ev: EstablishmentConstructedEvent) -> None:
        """Handle establishment construction."""
        self._state.establishment_id = ev.establishment_id or str(ev.aggregate_id)
        self._state.settlement_id = ev.settlement_id
        self._state.district_id = ev.district_id
        self._state.category = ev.category
        self._state.name = ev.name
        self._state.campaign_id = ev.campaign_id
        self._state.tier = ev.tier
        self._state.capacity = ev.capacity
        self._state.operating_cost = ev.operating_cost
        self._state.amenities = list(ev.amenities)
        self._state.owner_id = ev.owner_id
        self._state.status = "operational"
        self._state.is_constructed = True
        self._state.metadata = dict(ev.metadata)

    @handles(EstablishmentUpgradedEvent)
    def handle_upgraded(self, ev: EstablishmentUpgradedEvent) -> None:
        """Handle establishment upgrade."""
        self._state.tier = ev.tier
        if ev.capacity > 0:
            self._state.capacity = ev.capacity
        if ev.operating_cost > 0:
            self._state.operating_cost = ev.operating_cost
        for a in ev.added_amenities:
            if a not in self._state.amenities:
                self._state.amenities.append(a)

    def construct(
        self,
        settlement_id: str,
        district_id: str,
        category: str,
        name: str,
        campaign_id: str = "",
        tier: int = 1,
        capacity: int = 10,
        operating_cost: int = 5,
        amenities: list[str] | None = None,
        owner_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Construct a new establishment within a settlement district."""
        if self._state.is_constructed:
            raise ValueError(f"Establishment '{self.aggregate_id}' has already been constructed")

        valid_categories = {c.value for c in EstablishmentCategory}
        if category.lower() not in valid_categories:
            cats = ", ".join(valid_categories)
            raise ValueError(f"Invalid establishment category '{category}'. Must be one of: {cats}")

        if capacity <= 0:
            raise ValueError(f"Capacity must be greater than 0, got {capacity}")
        if operating_cost < 0:
            raise ValueError(f"Operating cost cannot be negative, got {operating_cost}")

        eid = str(self.aggregate_id or uuid4())
        self.create_event(
            EstablishmentConstructedEvent,
            aggregate_id=_to_uuid(eid),
            establishment_id=eid,
            settlement_id=str(settlement_id),
            district_id=str(district_id),
            category=category.lower(),
            name=name,
            campaign_id=str(campaign_id),
            tier=tier,
            capacity=capacity,
            operating_cost=operating_cost,
            amenities=amenities or [],
            owner_id=owner_id,
            metadata=metadata or {},
        )
        return eid

    def upgrade(
        self,
        new_tier: int | None = None,
        added_amenities: list[str] | None = None,
        capacity: int | None = None,
        operating_cost: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Upgrade establishment tier, amenities, and capacity."""
        if not self._state.is_constructed:
            raise ValueError(f"Establishment '{self.aggregate_id}' is not yet constructed")

        tier = new_tier if new_tier is not None else self._state.tier + 1
        if tier <= self._state.tier:
            raise ValueError(
                f"Upgrade tier ({tier}) must be greater than current tier ({self._state.tier})"
            )

        new_capacity = capacity if capacity is not None else self._state.capacity + 5
        new_cost = operating_cost if operating_cost is not None else self._state.operating_cost + 2
        eid = str(self._state.establishment_id or self.aggregate_id)

        self.create_event(
            EstablishmentUpgradedEvent,
            aggregate_id=_to_uuid(eid),
            establishment_id=eid,
            settlement_id=self._state.settlement_id,
            tier=tier,
            added_amenities=added_amenities or [],
            capacity=new_capacity,
            operating_cost=new_cost,
            metadata=metadata or {},
        )
        return tier
