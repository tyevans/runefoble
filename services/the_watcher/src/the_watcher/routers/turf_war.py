"""API router for faction turf wars, skirmish simulation, and regional unrest."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from the_watcher.dependencies import (
    require_campaign_permission,
)
from the_watcher.identity import CallerId, get_principal
from the_watcher.turf_war.models import (
    RegionalUnrestResponse,
    SkirmishSimulateRequest,
    SkirmishSimulateResponse,
)
from the_watcher.turf_war.service import (
    execute_skirmish_simulation,
    load_or_create_unrest,
)

router = APIRouter(dependencies=[Depends(get_principal)], tags=["turf_war"])


@router.post(
    "/api/v1/factions/skirmish/simulate",
    response_model=SkirmishSimulateResponse,
)
async def simulate_skirmish(
    caller_id: CallerId,
    req: SkirmishSimulateRequest,
) -> SkirmishSimulateResponse:
    """Simulate an ad-hoc boundary skirmish and escalate regional unrest."""
    await require_campaign_permission(caller_id, req.campaign_id, "campaign.run_session")
    return await execute_skirmish_simulation(req)


@router.get(
    "/api/v1/regions/{region_id}/unrest",
    response_model=RegionalUnrestResponse,
)
async def get_regional_unrest(
    caller_id: CallerId,
    region_id: str,
    campaign_id: str | None = None,
) -> RegionalUnrestResponse:
    """Query regional unrest metrics, security posture, and economic friction."""
    agg = await load_or_create_unrest(region_id, campaign_id or "")
    camp = campaign_id or agg.state.campaign_id
    await require_campaign_permission(caller_id, camp, "campaign.view")

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
