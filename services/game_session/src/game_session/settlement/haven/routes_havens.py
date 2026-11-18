"""FastAPI APIRouter for settlement haven lifecycle, projections, and listing.

Governed by ADR-0001, ADR-0003, ADR-0007, ADR-0013, and PRD-0024.
"""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from game_session.dependencies import (
    get_campaign_settlements_index,
    get_event_bus,
    get_settlement_repository,
    get_spicedb_client,
)
from game_session.settlement.auth import (
    check_campaign_write_permission,
    write_settlement_relationships,
)
from game_session.settlement.auth.tokens import CallerId, get_caller_principal
from game_session.settlement.haven.loaders import (
    build_settlement_projection,
    load_settlement,
    save_and_publish,
    to_uuid,
)
from game_session.settlement.models import (
    FoundSettlementRequest,
    SettlementProjectionResponse,
)
from game_session.settlement.settlement_aggregate import SettlementAggregate

router = APIRouter(dependencies=[Depends(get_caller_principal)])


@router.post("/api/v1/campaigns/{campaign_id}/settlements", status_code=201)
@router.post("/campaigns/{campaign_id}/settlements", status_code=201)
async def found_settlement(
    caller_id: CallerId,
    campaign_id: str,
    req: FoundSettlementRequest,
) -> SettlementProjectionResponse:
    """Found a new settlement haven with scale, biome, and layout zoning."""
    spicedb, repo, bus = get_spicedb_client(), get_settlement_repository(), get_event_bus()
    await check_campaign_write_permission(spicedb, campaign_id, caller_id)

    sid = uuid4()
    agg = SettlementAggregate(sid)
    try:
        agg.found(
            name=req.name,
            campaign_id=campaign_id,
            scale=req.scale,
            biome=req.biome,
            coordinates=req.coordinates,
            prosperity=req.prosperity,
            districts=req.districts,
            founded_by=caller_id,
            metadata=req.metadata,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    await save_and_publish(repo, bus, agg)
    await write_settlement_relationships(
        spicedb,
        settlement_id=str(sid),
        campaign_id=campaign_id,
        founder_id=caller_id,
    )

    get_campaign_settlements_index().setdefault(campaign_id, []).append(str(sid))
    return await build_settlement_projection(agg)


@router.get("/api/v1/campaigns/{campaign_id}/settlements/{settlement_id}")
@router.get("/campaigns/{campaign_id}/settlements/{settlement_id}")
async def get_campaign_settlement_projection(
    caller_id: CallerId,
    campaign_id: str,
    settlement_id: str,
) -> SettlementProjectionResponse:
    """Query settlement projection including scale, districts, and establishments."""
    agg = await load_settlement(settlement_id, "view", caller_id)
    if agg.state.campaign_id and agg.state.campaign_id != campaign_id:
        raise HTTPException(
            status_code=404, detail="Settlement does not belong to specified campaign"
        )
    return await build_settlement_projection(agg)


@router.get("/api/v1/campaigns/{campaign_id}/settlements")
@router.get("/campaigns/{campaign_id}/settlements")
async def list_campaign_settlements(
    caller_id: CallerId,
    campaign_id: str,
) -> list[SettlementProjectionResponse]:
    """List all settlement projections founded for a campaign."""
    sids = get_campaign_settlements_index().get(campaign_id, [])
    results: list[SettlementProjectionResponse] = []
    repo = get_settlement_repository()
    for sid in sids:
        try:
            agg = await repo.load(to_uuid(sid))
            if agg.state.is_founded:
                results.append(await build_settlement_projection(agg))
        except Exception:
            continue
    return results


__all__ = [
    "found_settlement",
    "get_campaign_settlement_projection",
    "list_campaign_settlements",
    "router",
]
