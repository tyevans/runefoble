"""API router for autonomous NPC faction simulation, agendas, and world ticks."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from runefoble_platform.aggregate_loading import load_if_exists
from runefoble_platform.identifiers import opaque_aggregate_id
from the_watcher.container_access import Engines, EventBus, Repos
from the_watcher.dependencies import check_dm_authorization, require_campaign_permission
from the_watcher.faction_models import (
    FactionCreateRequest,
    FactionResponse,
    WorldTickRequest,
    WorldTickResponse,
)
from the_watcher.factions import FactionAggregate
from the_watcher.identity import CallerId, get_principal

router = APIRouter(dependencies=[Depends(get_principal)], tags=["factions"])


@router.post(
    "/api/v1/campaigns/{campaign_id}/world-tick",
    response_model=WorldTickResponse,
)
async def advance_world_tick(
    repos: Repos,
    engines: Engines,
    event_bus: EventBus,
    caller_id: CallerId,
    campaign_id: str,
    req: WorldTickRequest | None = None,
) -> WorldTickResponse:
    """Execute an autonomous background simulation tick for all campaign factions."""
    await require_campaign_permission(caller_id, campaign_id, "campaign.run_session")
    engine = engines.faction_simulation
    tick_req = req or WorldTickRequest()
    return await engine.execute_world_tick(
        campaign_id,
        tick_req,
        faction_repo=repos.factions,
        world_repo=repos.campaign_worlds,
        bus=event_bus.get(),
    )


@router.post(
    "/api/v1/campaigns/{campaign_id}/factions",
    response_model=FactionResponse,
)
async def create_faction(
    repos: Repos,
    engines: Engines,
    caller_id: CallerId,
    campaign_id: str,
    req: FactionCreateRequest,
) -> FactionResponse:
    """Register and persist a new autonomous NPC faction within the campaign."""
    await require_campaign_permission(caller_id, campaign_id, "campaign.run_session")
    faction_id = f"faction-{uuid4().hex[:8]}"
    agg_uuid = opaque_aggregate_id(faction_id, field="faction_id")
    repo = repos.factions

    agg = FactionAggregate(aggregate_id=agg_uuid)
    agg.initialize(
        campaign_id=campaign_id,
        faction_id=faction_id,
        name=req.name,
        influence=req.influence,
        resources=req.resources,
        disposition=req.disposition,
        active_goal=req.active_goal,
        rival_faction_ids=req.rival_faction_ids,
        territory=req.territory,
        metadata=req.metadata,
    )
    await repo.save(agg)

    engine = engines.faction_simulation
    await engine.register_faction(campaign_id, faction_id, repos.campaign_worlds)

    return FactionResponse(
        faction_id=agg.state.faction_id,
        campaign_id=agg.state.campaign_id,
        name=agg.state.name,
        influence=agg.state.influence,
        resources=agg.state.resources,
        disposition=agg.state.disposition,
        active_goal=agg.state.active_goal,
        goal_progress=agg.state.goal_progress,
        goal_target=agg.state.goal_target,
        rival_faction_ids=agg.state.rival_faction_ids,
        territory=agg.state.territory,
        shifts=agg.state.shifts,
        history=agg.state.history,
    )


@router.get(
    "/api/v1/campaigns/{campaign_id}/factions",
    response_model=list[FactionResponse],
)
async def list_factions(
    repos: Repos,
    engines: Engines,
    caller_id: CallerId,
    campaign_id: str,
) -> list[FactionResponse]:
    """List all registered and simulated factions for a campaign."""
    await require_campaign_permission(caller_id, campaign_id, "campaign.view")
    engine = engines.faction_simulation

    factions = await engine.ensure_default_factions(
        campaign_id, repos.factions, repos.campaign_worlds
    )
    responses: list[FactionResponse] = []
    for f in factions:
        responses.append(
            FactionResponse(
                faction_id=f.state.faction_id,
                campaign_id=f.state.campaign_id,
                name=f.state.name,
                influence=f.state.influence,
                resources=f.state.resources,
                disposition=f.state.disposition,
                active_goal=f.state.active_goal,
                goal_progress=f.state.goal_progress,
                goal_target=f.state.goal_target,
                rival_faction_ids=f.state.rival_faction_ids,
                territory=f.state.territory,
                shifts=f.state.shifts,
                history=f.state.history,
            )
        )
    return responses


@router.get(
    "/api/v1/campaigns/{campaign_id}/factions/{faction_id}",
    response_model=FactionResponse,
)
async def get_faction(
    repos: Repos,
    caller_id: CallerId,
    campaign_id: str,
    faction_id: str,
) -> FactionResponse:
    """Retrieve detailed aggregate state for a specific campaign faction."""
    await require_campaign_permission(caller_id, campaign_id, "campaign.view")
    repo = repos.factions
    agg = await load_if_exists(repo, opaque_aggregate_id(faction_id, field="faction_id"))
    if agg is None:
        raise HTTPException(status_code=404, detail="Faction not found")
    return FactionResponse(
        faction_id=agg.state.faction_id,
        campaign_id=agg.state.campaign_id,
        name=agg.state.name,
        influence=agg.state.influence,
        resources=agg.state.resources,
        disposition=agg.state.disposition,
        active_goal=agg.state.active_goal,
        goal_progress=agg.state.goal_progress,
        goal_target=agg.state.goal_target,
        rival_faction_ids=agg.state.rival_faction_ids,
        territory=agg.state.territory,
        shifts=agg.state.shifts,
        history=agg.state.history,
    )


@router.get(
    "/api/v1/campaigns/{campaign_id}/world-ticks/latest",
    response_model=WorldTickResponse,
)
async def get_latest_bulletin(
    repos: Repos,
    engines: Engines,
    caller_id: CallerId,
    campaign_id: str,
) -> WorldTickResponse:
    """Retrieve the most recent DM intelligence bulletin and world progression state."""
    await require_campaign_permission(caller_id, campaign_id, "campaign.view")
    engine = engines.faction_simulation
    bulletin = await engine.get_latest_bulletin(campaign_id, repos.factions, repos.campaign_worlds)
    if not bulletin:
        raise HTTPException(
            status_code=404,
            detail="No world tick has been executed for this campaign yet",
        )
    is_dm = await check_dm_authorization(caller_id, campaign_id=campaign_id)
    if not is_dm:
        redacted = bulletin.model_copy()
        redacted.intelligence_bulletin = ""
        return redacted
    return bulletin
