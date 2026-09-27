"""API router for faction turf wars, skirmish simulation, and regional unrest."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException
from the_watcher.dependencies import (
    check_dm_authorization,
    get_spicedb_client,
)
from the_watcher.turf_war.models import (
    RegionalUnrestResponse,
    SkirmishSimulateRequest,
    SkirmishSimulateResponse,
)
from the_watcher.turf_war.service import (
    execute_skirmish_simulation,
    load_or_create_unrest,
)

router = APIRouter(tags=["turf_war"])


async def _assert_dm_permission(caller: str | None, campaign_id: str | None) -> None:
    """Enforce Zanzibar authorization: only DMs/GMs can trigger turf war skirmishes."""
    if not caller or not campaign_id:
        return
    client = get_spicedb_client()
    if not await check_dm_authorization(caller, campaign_id=campaign_id, spicedb=client):
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Requires DM or campaign owner permission to simulate skirmishes.",
        )


async def _assert_view_permission(caller: str | None, campaign_id: str | None) -> None:
    """Enforce Zanzibar authorization: campaign members and spectators can view regional unrest."""
    if not caller or not campaign_id:
        return
    client = get_spicedb_client()
    can_view = await client.check_permission("campaign", str(campaign_id), "view", "user", caller)
    if not can_view and not await check_dm_authorization(
        caller, campaign_id=campaign_id, spicedb=client
    ):
        raise HTTPException(
            status_code=403,
            detail="Forbidden: User lacks campaign view permission for regional unrest.",
        )


@router.post(
    "/the-watcher/factions/skirmish/simulate",
    response_model=SkirmishSimulateResponse,
)
@router.post(
    "/api/v1/factions/skirmish/simulate",
    response_model=SkirmishSimulateResponse,
)
async def simulate_skirmish(
    req: SkirmishSimulateRequest,
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
) -> SkirmishSimulateResponse:
    """Simulate an ad-hoc boundary skirmish and escalate regional unrest."""
    await _assert_dm_permission(x_user_id, req.campaign_id)
    return await execute_skirmish_simulation(req)


@router.get(
    "/the-watcher/regions/{region_id}/unrest",
    response_model=RegionalUnrestResponse,
)
@router.get(
    "/api/v1/regions/{region_id}/unrest",
    response_model=RegionalUnrestResponse,
)
async def get_regional_unrest(
    region_id: str,
    campaign_id: str | None = None,
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
) -> RegionalUnrestResponse:
    """Query regional unrest metrics, security posture, and economic friction."""
    agg = await load_or_create_unrest(region_id, campaign_id or "")
    camp = campaign_id or agg.state.campaign_id
    if camp and x_user_id:
        await _assert_view_permission(x_user_id, camp)

    return RegionalUnrestResponse(
        region_id=agg.state.region_id,
        campaign_id=agg.state.campaign_id,
        controlling_faction_id=agg.state.controlling_faction_id,
        unrest_score=agg.state.unrest_score,
        alert_level=agg.state.alert_level,
        security_level=agg.state.security_level,
        economic_friction=agg.state.economic_friction,
        contested_nodes=agg.state.contested_nodes,
        recent_skirmishes=agg.state.recent_skirmishes,
    )
