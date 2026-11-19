"""FastAPI APIRouter for establishment zoning, creation, and inspection.

Governed by ADR-0001, ADR-0003, ADR-0007, ADR-0013, and PRD-0024.
"""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from game_session.child_index import ChildIndexKind
from game_session.dependencies import get_establishment_repository, get_event_bus
from game_session.queries import link_child, list_establishments_for_settlement
from game_session.settlement.auth import (
    write_establishment_relationships,
)
from game_session.settlement.auth.tokens import CallerId, get_principal
from game_session.settlement.establishment_aggregate import EstablishmentAggregate
from game_session.settlement.haven.loaders import (
    load_establishment,
    load_settlement,
    save_and_publish,
)
from game_session.settlement.models import (
    ConstructEstablishmentRequest,
    EstablishmentState,
)
from runefoble_auth.factory import get_spicedb_client
from runefoble_platform.aggregate_loading import load_if_exists
from runefoble_platform.identifiers import parse_uuid

router = APIRouter(dependencies=[Depends(get_principal)])


@router.post("/api/v1/settlements/{settlement_id}/establishments", status_code=201)
@router.post("/settlements/{settlement_id}/establishments", status_code=201)
async def construct_establishment(
    caller_id: CallerId,
    settlement_id: str,
    req: ConstructEstablishmentRequest,
) -> EstablishmentState:
    """Construct a commercial, civic, or hospitality establishment within a district."""
    settlement = await load_settlement(settlement_id, "upgrade", caller_id)
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
            owner_id=caller_id,
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
        owner_id=caller_id,
    )

    await link_child(ChildIndexKind.SETTLEMENT_ESTABLISHMENTS, settlement_id, str(eid))
    return est_agg.state


@router.get("/api/v1/settlements/{settlement_id}/establishments")
@router.get("/settlements/{settlement_id}/establishments")
async def list_settlement_establishments(
    caller_id: CallerId,
    settlement_id: str,
) -> list[EstablishmentState]:
    """List all establishments located in a settlement."""
    await load_settlement(settlement_id, "view", caller_id)
    est_ids = await list_establishments_for_settlement(settlement_id)
    est_repo = get_establishment_repository()
    results: list[EstablishmentState] = []
    for eid in est_ids:
        agg = await load_if_exists(est_repo, parse_uuid(eid, field="establishment_id"))
        if agg is not None and agg.state.is_constructed:
            results.append(agg.state)
    return results


@router.get("/api/v1/establishments/{establishment_id}")
@router.get("/establishments/{establishment_id}")
async def get_establishment(
    caller_id: CallerId,
    establishment_id: str,
) -> EstablishmentState:
    """Retrieve establishment details and operational stats."""
    agg = await load_establishment(establishment_id, "view", caller_id)
    return agg.state


__all__ = [
    "construct_establishment",
    "get_establishment",
    "list_settlement_establishments",
    "router",
]
