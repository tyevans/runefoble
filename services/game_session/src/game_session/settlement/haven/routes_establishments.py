"""FastAPI APIRouter for establishment zoning, creation, and inspection.

Governed by ADR-0001, ADR-0003, ADR-0007, ADR-0013, and PRD-0024.
"""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException
from game_session.dependencies import (
    get_establishment_repository,
    get_event_bus,
    get_settlement_establishments_index,
    get_spicedb_client,
)
from game_session.settlement.auth import (
    write_establishment_relationships,
)
from game_session.settlement.establishment_aggregate import EstablishmentAggregate
from game_session.settlement.haven.loaders import (
    load_establishment,
    load_settlement,
    save_and_publish,
    to_uuid,
)
from game_session.settlement.models import (
    ConstructEstablishmentRequest,
    EstablishmentState,
)

router = APIRouter()


@router.post("/api/v1/settlements/{settlement_id}/establishments", status_code=201)
@router.post("/settlements/{settlement_id}/establishments", status_code=201)
async def construct_establishment(
    settlement_id: str,
    req: ConstructEstablishmentRequest,
    x_user_id: str | None = Header(default=None),
) -> EstablishmentState:
    """Construct a commercial, civic, or hospitality establishment within a district."""
    settlement = await load_settlement(settlement_id, "upgrade", x_user_id)
    if req.district_id not in settlement.state.districts:
        raise HTTPException(
            status_code=400,
            detail=(
                f"District '{req.district_id}' is not zoned or unlocked in settlement '{settlement_id}'. "
                f"Available districts: {settlement.state.districts}"
            ),
        )

    spicedb, est_repo, bus = (
        get_spicedb_client(),
        get_establishment_repository(),
        get_event_bus(),
    )
    eid = uuid4()
    est_agg = EstablishmentAggregate(eid)
    try:
        est_agg.construct(
            settlement_id=settlement_id,
            district_id=req.district_id,
            category=req.category,
            name=req.name,
            campaign_id=settlement.state.campaign_id,
            tier=req.tier,
            capacity=req.capacity,
            operating_cost=req.operating_cost,
            amenities=req.amenities,
            owner_id=x_user_id or "system",
            metadata=req.metadata,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    await save_and_publish(est_repo, bus, est_agg)
    await write_establishment_relationships(
        spicedb,
        establishment_id=str(eid),
        settlement_id=settlement_id,
        campaign_id=settlement.state.campaign_id,
        owner_id=x_user_id,
    )

    get_settlement_establishments_index().setdefault(settlement_id, []).append(str(eid))
    return est_agg.state


@router.get("/api/v1/settlements/{settlement_id}/establishments")
@router.get("/settlements/{settlement_id}/establishments")
async def list_settlement_establishments(
    settlement_id: str,
    x_user_id: str | None = Header(default=None),
) -> list[EstablishmentState]:
    """List all establishments located in a settlement."""
    await load_settlement(settlement_id, "view", x_user_id)
    est_ids = get_settlement_establishments_index().get(settlement_id, [])
    est_repo = get_establishment_repository()
    results: list[EstablishmentState] = []
    for eid in est_ids:
        try:
            agg = await est_repo.load(to_uuid(eid))
            if agg.state.is_constructed:
                results.append(agg.state)
        except Exception:
            continue
    return results


@router.get("/api/v1/establishments/{establishment_id}")
@router.get("/establishments/{establishment_id}")
async def get_establishment(
    establishment_id: str,
    x_user_id: str | None = Header(default=None),
) -> EstablishmentState:
    """Retrieve establishment details and operational stats."""
    agg = await load_establishment(establishment_id, "view", x_user_id)
    return agg.state


__all__ = [
    "construct_establishment",
    "get_establishment",
    "list_settlement_establishments",
    "router",
]
