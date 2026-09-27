"""API router for autonomous NPC faction simulation, agendas, and world ticks."""

from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException
from the_watcher.dependencies import (
    check_dm_authorization,
    get_event_bus,
    get_faction_repo,
    get_faction_simulation_engine,
    get_spicedb_client,
    to_uuid,
)
from the_watcher.faction_models import (
    FactionCreateRequest,
    FactionResponse,
    WorldTickRequest,
    WorldTickResponse,
)
from the_watcher.factions import FactionAggregate

router = APIRouter(tags=["factions"])


async def _assert_dm_permission(caller: str | None, campaign_id: str) -> None:
    """Enforce SpiceDB Zanzibar authorization: only DMs/GMs/owners can mutate or tick world state."""
    if not caller:
        return
    client = get_spicedb_client()
    is_dm = await check_dm_authorization(caller, campaign_id=campaign_id, spicedb=client)
    if not is_dm:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Zanzibar authorization denied. Requires DM or campaign owner permission.",
        )


async def _assert_view_permission(caller: str | None, campaign_id: str) -> None:
    """Enforce SpiceDB Zanzibar authorization: campaign members and spectators can view factions."""
    if not caller:
        return
    client = get_spicedb_client()
    can_view = await client.check_permission("campaign", str(campaign_id), "view", "user", caller)
    if not can_view:
        can_dm = await check_dm_authorization(caller, campaign_id=campaign_id, spicedb=client)
        if not can_dm:
            raise HTTPException(
                status_code=403,
                detail="Forbidden: Zanzibar authorization denied. User lacks campaign view permission.",
            )


@router.post(
    "/api/v1/campaigns/{campaign_id}/world-tick",
    response_model=WorldTickResponse,
)
@router.post(
    "/api/v1/campaigns/{campaign_id}/factions/tick",
    response_model=WorldTickResponse,
)
async def advance_world_tick(
    campaign_id: str,
    req: WorldTickRequest | None = None,
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
) -> WorldTickResponse:
    """Execute an autonomous background simulation tick for all campaign factions."""
    await _assert_dm_permission(x_user_id, campaign_id)
    engine = get_faction_simulation_engine()
    repo = get_faction_repo()
    tick_req = req or WorldTickRequest()
    return await engine.execute_world_tick(campaign_id, tick_req, repo, bus=get_event_bus())


@router.post(
    "/api/v1/campaigns/{campaign_id}/factions",
    response_model=FactionResponse,
)
async def create_faction(
    campaign_id: str,
    req: FactionCreateRequest,
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
) -> FactionResponse:
    """Register and persist a new autonomous NPC faction within the campaign."""
    await _assert_dm_permission(x_user_id, campaign_id)
    faction_id = f"faction-{uuid4().hex[:8]}"
    agg_uuid = to_uuid(faction_id)
    repo = get_faction_repo()

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

    engine = get_faction_simulation_engine()
    engine.register_faction_id(campaign_id, faction_id)

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
    campaign_id: str,
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
) -> list[FactionResponse]:
    """List all registered and simulated factions for a campaign."""
    await _assert_view_permission(x_user_id, campaign_id)
    engine = get_faction_simulation_engine()
    repo = get_faction_repo()

    factions = await engine.ensure_default_factions(campaign_id, repo)
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
    campaign_id: str,
    faction_id: str,
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
) -> FactionResponse:
    """Retrieve detailed aggregate state for a specific campaign faction."""
    await _assert_view_permission(x_user_id, campaign_id)
    repo = get_faction_repo()
    try:
        agg = await repo.load(to_uuid(faction_id))
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
    except Exception as exc:
        raise HTTPException(status_code=404, detail="Faction not found") from exc


@router.get(
    "/api/v1/campaigns/{campaign_id}/world-ticks/latest",
    response_model=WorldTickResponse,
)
async def get_latest_bulletin(
    campaign_id: str,
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
) -> WorldTickResponse:
    """Retrieve the most recent DM intelligence bulletin and world progression state."""
    await _assert_view_permission(x_user_id, campaign_id)
    engine = get_faction_simulation_engine()
    bulletin = engine.get_latest_bulletin(campaign_id)
    if not bulletin:
        raise HTTPException(
            status_code=404,
            detail="No world tick has been executed for this campaign yet",
        )
    if x_user_id:
        client = get_spicedb_client()
        is_dm = await check_dm_authorization(x_user_id, campaign_id=campaign_id, spicedb=client)
        if not is_dm:
            redacted = bulletin.model_copy()
            redacted.intelligence_bulletin = ""
            return redacted
    return bulletin
