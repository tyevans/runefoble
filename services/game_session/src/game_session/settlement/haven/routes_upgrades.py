"""FastAPI APIRouter for civic tier scaling and establishment facility upgrades.

Governed by ADR-0001, ADR-0003, ADR-0007, ADR-0013, and PRD-0024.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from game_session.dependencies import (
    get_establishment_repository,
    get_event_bus,
    get_settlement_repository,
)
from game_session.events import STREAM_WEST_MARCHES
from game_session.settlement.auth.tokens import CallerId, get_principal
from game_session.settlement.haven.loaders import (
    build_settlement_projection,
    load_establishment,
    load_settlement,
)
from game_session.settlement.models import (
    EstablishmentState,
    SettlementProjectionResponse,
    UpgradeEstablishmentRequest,
    UpgradeSettlementTierRequest,
)
from runefoble_platform.event_publish import publish_aggregate_events

router = APIRouter(dependencies=[Depends(get_principal)])


@router.post("/api/v1/settlements/{settlement_id}/upgrade-tier")
async def upgrade_settlement_tier(
    caller_id: CallerId,
    settlement_id: str,
    req: UpgradeSettlementTierRequest,
) -> SettlementProjectionResponse:
    """Upgrade settlement to higher civic tier."""
    agg = await load_settlement(settlement_id, "upgrade", caller_id)
    try:
        agg.upgrade_tier(
            new_tier=req.new_tier,
            target_scale=req.target_scale,
            prosperity=req.prosperity,
            metadata=req.metadata,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    events = list(agg.uncommitted_events)
    await get_settlement_repository().save(agg)
    if bus := get_event_bus():
        await publish_aggregate_events(bus, STREAM_WEST_MARCHES, events)
    return await build_settlement_projection(agg)


@router.post("/api/v1/establishments/{establishment_id}/upgrade")
async def upgrade_establishment(
    caller_id: CallerId,
    establishment_id: str,
    req: UpgradeEstablishmentRequest,
) -> EstablishmentState:
    """Upgrade establishment tier, amenities, or capacity."""
    agg = await load_establishment(establishment_id, "edit", caller_id)
    try:
        agg.upgrade(
            new_tier=req.tier,
            added_amenities=req.added_amenities,
            capacity=req.capacity,
            operating_cost=req.operating_cost,
            metadata=req.metadata,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    events = list(agg.uncommitted_events)
    await get_establishment_repository().save(agg)
    if bus := get_event_bus():
        await publish_aggregate_events(bus, STREAM_WEST_MARCHES, events)
    return agg.state


__all__ = [
    "router",
    "upgrade_establishment",
    "upgrade_settlement_tier",
]
