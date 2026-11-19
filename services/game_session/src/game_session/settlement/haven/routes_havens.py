"""FastAPI APIRouter for settlement haven lifecycle, projections, and listing.

Governed by ADR-0001, ADR-0003, ADR-0007, ADR-0013, and PRD-0024.
"""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from game_session.settlement.auth import (
    check_campaign_write_permission,
    write_settlement_relationships,
)
from game_session.settlement.child_indexes import (
    SettlementChildIndex,
    list_settlements_for_campaign,
)
from game_session.settlement.haven.loaders import (
    build_settlement_projection,
    load_settlement,
)
from game_session.settlement.models import (
    FoundSettlementRequest,
    SettlementProjectionResponse,
)
from game_session.settlement.repositories import SettlementRepos
from game_session.settlement.settlement_aggregate import SettlementAggregate
from game_session.shared.child_index_queries import ChildIndexes, link_child
from game_session.shared.container_access import EventBus
from game_session.shared.identity import CallerId, get_principal
from game_session.shared.streams import STREAM_WEST_MARCHES
from runefoble_auth.factory import get_spicedb_client
from runefoble_platform.aggregate_loading import load_if_exists
from runefoble_platform.event_publish import publish_aggregate_events
from runefoble_platform.identifiers import parse_uuid

router = APIRouter(dependencies=[Depends(get_principal)])


@router.post("/api/v1/campaigns/{campaign_id}/settlements", status_code=201)
async def found_settlement(
    caller_id: CallerId,
    campaign_id: str,
    req: FoundSettlementRequest,
    repos: SettlementRepos,
    event_bus: EventBus,
    child_indexes: ChildIndexes,
) -> SettlementProjectionResponse:
    """Found a new settlement haven with scale, biome, and layout zoning."""
    spicedb, repo, bus = get_spicedb_client(), repos.settlements, event_bus.get()
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

    events = list(agg.uncommitted_events)
    await repo.save(agg)
    await write_settlement_relationships(
        spicedb,
        settlement_id=str(sid),
        campaign_id=campaign_id,
        founder_id=caller_id,
    )

    await link_child(
        child_indexes, SettlementChildIndex.CAMPAIGN_SETTLEMENTS, campaign_id, str(sid)
    )
    if bus:
        await publish_aggregate_events(bus, STREAM_WEST_MARCHES, events)
    return await build_settlement_projection(repos, child_indexes, agg)


@router.get("/api/v1/campaigns/{campaign_id}/settlements/{settlement_id}")
async def get_campaign_settlement_projection(
    caller_id: CallerId,
    campaign_id: str,
    settlement_id: str,
    repos: SettlementRepos,
    child_indexes: ChildIndexes,
) -> SettlementProjectionResponse:
    """Query settlement projection including scale, districts, and establishments."""
    agg = await load_settlement(repos, settlement_id, "view", caller_id)
    if agg.state.campaign_id and agg.state.campaign_id != campaign_id:
        raise HTTPException(
            status_code=404, detail="Settlement does not belong to specified campaign"
        )
    return await build_settlement_projection(repos, child_indexes, agg)


@router.get("/api/v1/campaigns/{campaign_id}/settlements")
async def list_campaign_settlements(
    caller_id: CallerId,
    campaign_id: str,
    repos: SettlementRepos,
    child_indexes: ChildIndexes,
) -> list[SettlementProjectionResponse]:
    """List all settlement projections founded for a campaign."""
    sids = await list_settlements_for_campaign(child_indexes, campaign_id)
    results: list[SettlementProjectionResponse] = []
    repo = repos.settlements
    for sid in sids:
        agg = await load_if_exists(repo, parse_uuid(sid, field="settlement_id"))
        if agg is not None and agg.state.is_founded:
            results.append(await build_settlement_projection(repos, child_indexes, agg))
    return results


__all__ = [
    "found_settlement",
    "get_campaign_settlement_projection",
    "list_campaign_settlements",
    "router",
]
