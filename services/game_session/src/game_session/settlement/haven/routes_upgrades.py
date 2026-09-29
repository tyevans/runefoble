"""FastAPI APIRouter for civic tier scaling and establishment facility upgrades.

Governed by ADR-0001, ADR-0003, ADR-0007, ADR-0013, and PRD-0024.
"""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from game_session.dependencies import (
    get_establishment_repository,
    get_event_bus,
    get_settlement_repository,
)
from game_session.settlement.haven.loaders import (
    build_settlement_projection,
    load_establishment,
    load_settlement,
    save_and_publish,
)
from game_session.settlement.models import (
    EstablishmentState,
    SettlementProjectionResponse,
    UpgradeEstablishmentRequest,
    UpgradeSettlementTierRequest,
)

router = APIRouter()


@router.post("/api/v1/settlements/{settlement_id}/upgrade-tier")
@router.post("/settlements/{settlement_id}/upgrade-tier")
async def upgrade_settlement_tier(
    settlement_id: str,
    req: UpgradeSettlementTierRequest,
    x_user_id: str | None = Header(default=None),
) -> SettlementProjectionResponse:
    """Upgrade settlement to higher civic tier."""
    agg = await load_settlement(settlement_id, "upgrade", x_user_id)
    try:
        agg.upgrade_tier(
            new_tier=req.new_tier,
            target_scale=req.target_scale,
            prosperity=req.prosperity,
            metadata=req.metadata,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    await save_and_publish(get_settlement_repository(), get_event_bus(), agg)
    return await build_settlement_projection(agg)


@router.post("/api/v1/establishments/{establishment_id}/upgrade")
@router.post("/establishments/{establishment_id}/upgrade")
async def upgrade_establishment(
    establishment_id: str,
    req: UpgradeEstablishmentRequest,
    x_user_id: str | None = Header(default=None),
) -> EstablishmentState:
    """Upgrade establishment tier, amenities, or capacity."""
    agg = await load_establishment(establishment_id, "manage", x_user_id)
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

    await save_and_publish(get_establishment_repository(), get_event_bus(), agg)
    return agg.state


__all__ = [
    "router",
    "upgrade_establishment",
    "upgrade_settlement_tier",
]
