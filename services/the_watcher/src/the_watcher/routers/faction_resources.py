"""API router for faction economic assets, mercenary recruitment, and bribery checks."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from runefoble_platform.aggregate_loading import load_or_create
from runefoble_platform.identifiers import opaque_aggregate_id
from the_watcher.dependencies import (
    get_faction_resource_repo,
    require_campaign_permission,
)
from the_watcher.factions.resources.aggregate import FactionResourceAggregate
from the_watcher.factions.resources.models import (
    BriberyAttemptRequest,
    BriberyAttemptResponse,
    FactionResourceResponse,
    MercenaryRecruitRequest,
    ResourceAdjustRequest,
)
from the_watcher.identity import CallerId, get_principal

router = APIRouter(dependencies=[Depends(get_principal)], tags=["faction_resources"])


async def _load_or_create(faction_id: str) -> FactionResourceAggregate:
    """Load the faction resource aggregate. Create an empty one only when its stream is absent."""
    repo = get_faction_resource_repo()
    agg_uuid = opaque_aggregate_id(faction_id, field="faction_id")

    def _fresh(aggregate_id: UUID) -> FactionResourceAggregate:
        agg = FactionResourceAggregate(aggregate_id=aggregate_id)
        agg.state.faction_id = faction_id
        return agg

    return await load_or_create(repo, agg_uuid, _fresh)


def _to_response(agg: FactionResourceAggregate) -> FactionResourceResponse:
    upkeep = sum(u.count * u.upkeep_per_tick for u in agg.state.mercenaries)
    return FactionResourceResponse(
        faction_id=agg.state.faction_id,
        campaign_id=agg.state.campaign_id,
        treasury=agg.state.treasury,
        contraband_score=agg.state.contraband_score,
        mercenaries_count=agg.state.total_mercenaries,
        upkeep_cost=upkeep,
        mercenaries=agg.state.mercenaries,
        contraband=agg.state.contraband,
    )


@router.post(
    "/api/v1/factions/{faction_id}/resources/adjust", response_model=FactionResourceResponse
)
async def adjust_resources(
    caller_id: CallerId,
    faction_id: str,
    req: ResourceAdjustRequest,
    campaign_id: str | None = None,
) -> FactionResourceResponse:
    agg = await _load_or_create(faction_id)
    camp = campaign_id or req.campaign_id or agg.state.campaign_id
    await require_campaign_permission(caller_id, camp, "campaign.run_session")
    agg.adjust_resources(req.treasury_delta, req.contraband_delta, req.reason, camp, req.metadata)
    await get_faction_resource_repo().save(agg)
    return _to_response(agg)


@router.post("/api/v1/factions/{faction_id}/bribery/resolve", response_model=BriberyAttemptResponse)
async def resolve_bribery(
    caller_id: CallerId,
    faction_id: str,
    req: BriberyAttemptRequest,
    campaign_id: str | None = None,
) -> BriberyAttemptResponse:
    agg = await _load_or_create(faction_id)
    camp = campaign_id or req.campaign_id or agg.state.campaign_id
    await require_campaign_permission(caller_id, camp, "campaign.run_session")
    try:
        r = agg.execute_bribery(
            req.target_name,
            req.target_role,
            req.bribe_amount,
            req.target_loyalty,
            req.counter_bribe,
            req.roll,
            camp,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await get_faction_resource_repo().save(agg)
    return BriberyAttemptResponse(
        faction_id=faction_id, target_name=req.target_name, bribe_amount=req.bribe_amount, **r
    )


@router.post(
    "/api/v1/factions/{faction_id}/mercenaries/recruit", response_model=FactionResourceResponse
)
async def recruit_mercenaries(
    caller_id: CallerId,
    faction_id: str,
    req: MercenaryRecruitRequest,
    campaign_id: str | None = None,
) -> FactionResourceResponse:
    agg = await _load_or_create(faction_id)
    camp = campaign_id or req.campaign_id or agg.state.campaign_id
    await require_campaign_permission(caller_id, camp, "campaign.run_session")
    try:
        agg.recruit_mercenaries(
            req.unit_name, req.count, req.cost_per_unit, req.unit_type, req.upkeep_per_tick, camp
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await get_faction_resource_repo().save(agg)
    return _to_response(agg)


@router.get("/api/v1/factions/{faction_id}/resources", response_model=FactionResourceResponse)
async def get_faction_resources(
    caller_id: CallerId,
    faction_id: str,
    campaign_id: str | None = None,
) -> FactionResourceResponse:
    agg = await _load_or_create(faction_id)
    await require_campaign_permission(
        caller_id, campaign_id or agg.state.campaign_id, "campaign.view"
    )
    return _to_response(agg)
