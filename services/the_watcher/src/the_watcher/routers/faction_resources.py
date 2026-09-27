"""API router for faction economic assets, mercenary recruitment, and bribery checks."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException
from the_watcher.dependencies import (
    check_dm_authorization,
    get_faction_resource_repo,
    get_spicedb_client,
    to_uuid,
)
from the_watcher.factions.resources.aggregate import FactionResourceAggregate
from the_watcher.factions.resources.models import (
    BriberyAttemptRequest,
    BriberyAttemptResponse,
    FactionResourceResponse,
    MercenaryRecruitRequest,
    ResourceAdjustRequest,
)

router = APIRouter(tags=["faction_resources"])


async def _assert_dm(caller: str | None, campaign_id: str | None) -> None:
    if (
        caller
        and campaign_id
        and not await check_dm_authorization(
            caller, campaign_id=campaign_id, spicedb=get_spicedb_client()
        )
    ):
        raise HTTPException(status_code=403, detail="Forbidden: Requires DM permission.")


async def _assert_view(caller: str | None, campaign_id: str | None) -> None:
    if caller and campaign_id:
        c = get_spicedb_client()
        if not await c.check_permission(
            "campaign", str(campaign_id), "view", "user", caller
        ) and not await check_dm_authorization(caller, campaign_id=campaign_id, spicedb=c):
            raise HTTPException(
                status_code=403, detail="Forbidden: Lacks campaign view permission."
            )


async def _load_or_create(faction_id: str) -> FactionResourceAggregate:
    repo = get_faction_resource_repo()
    agg_uuid = to_uuid(faction_id)
    try:
        return await repo.load(agg_uuid)
    except Exception:
        agg = FactionResourceAggregate(aggregate_id=agg_uuid)
        agg.state.faction_id = faction_id
        return agg


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


@router.post("/factions/{faction_id}/resources/adjust", response_model=FactionResourceResponse)
@router.post(
    "/api/v1/factions/{faction_id}/resources/adjust", response_model=FactionResourceResponse
)
async def adjust_resources(
    faction_id: str,
    req: ResourceAdjustRequest,
    campaign_id: str | None = None,
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
) -> FactionResourceResponse:
    agg = await _load_or_create(faction_id)
    camp = campaign_id or req.campaign_id or agg.state.campaign_id
    await _assert_dm(x_user_id, camp)
    agg.adjust_resources(req.treasury_delta, req.contraband_delta, req.reason, camp, req.metadata)
    await get_faction_resource_repo().save(agg)
    return _to_response(agg)


@router.post("/factions/{faction_id}/bribery/resolve", response_model=BriberyAttemptResponse)
@router.post("/api/v1/factions/{faction_id}/bribery/resolve", response_model=BriberyAttemptResponse)
async def resolve_bribery(
    faction_id: str,
    req: BriberyAttemptRequest,
    campaign_id: str | None = None,
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
) -> BriberyAttemptResponse:
    agg = await _load_or_create(faction_id)
    camp = campaign_id or req.campaign_id or agg.state.campaign_id
    await _assert_dm(x_user_id, camp)
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


@router.post("/factions/{faction_id}/mercenaries/recruit", response_model=FactionResourceResponse)
@router.post(
    "/api/v1/factions/{faction_id}/mercenaries/recruit", response_model=FactionResourceResponse
)
async def recruit_mercenaries(
    faction_id: str,
    req: MercenaryRecruitRequest,
    campaign_id: str | None = None,
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
) -> FactionResourceResponse:
    agg = await _load_or_create(faction_id)
    camp = campaign_id or req.campaign_id or agg.state.campaign_id
    await _assert_dm(x_user_id, camp)
    try:
        agg.recruit_mercenaries(
            req.unit_name, req.count, req.cost_per_unit, req.unit_type, req.upkeep_per_tick, camp
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await get_faction_resource_repo().save(agg)
    return _to_response(agg)


@router.get("/factions/{faction_id}/resources", response_model=FactionResourceResponse)
@router.get("/api/v1/factions/{faction_id}/resources", response_model=FactionResourceResponse)
async def get_faction_resources(
    faction_id: str,
    campaign_id: str | None = None,
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
) -> FactionResourceResponse:
    agg = await _load_or_create(faction_id)
    await _assert_view(x_user_id, campaign_id or agg.state.campaign_id)
    return _to_response(agg)
