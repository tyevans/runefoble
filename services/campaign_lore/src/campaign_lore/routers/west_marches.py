"""FastAPI router for West Marches shared atlas pins, stronghold dashboard, and tavern notices.

Part of TASK-0135 / PRD-0007 / PRD-0014 / US-0050 / US-0058 / ADR-0001 / ADR-0011.
Governed by Hard Invariant 1 (SpiceDB Zanzibar) and Hard Invariant 2 (eventsource-py).
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_platform.event_sourcing import AggregateRepository

from campaign_lore.dependencies import (
    check_user_can_play_campaign,
    check_user_can_view_campaign,
    get_current_user_id,
    get_spicedb_client,
    get_west_marches_repo,
)
from campaign_lore.west_marches_aggregate import (
    WestMarchesAtlasAggregate,
    WestMarchesState,
)

router = APIRouter(
    prefix="/api/v1/campaigns/{campaign_id}/west-marches",
    tags=["West Marches Atlas"],
)


class RecordDiscoveryPayload(BaseModel):
    """Payload to record a shared frontier milestone or point of interest."""

    name: str = Field(description="Milestone or dungeon title")
    discovery_type: str = Field(default="dungeon", description="Discovery category")
    coordinates: dict[str, float] = Field(description="Map coordinates {x, y}")
    discovered_by_party_name: str = Field(
        default="Adventurers", description="Discovering adventuring party name"
    )
    description: str = Field(default="", description="Narrative description")
    danger_level: int = Field(default=1, ge=1, le=5, description="Danger rating 1-5")
    discovery_id: str | None = Field(default=None, description="Optional custom ID")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Custom metadata")


class UpgradeStrongholdPayload(BaseModel):
    """Payload to upgrade a communal outpost or stronghold facility."""

    facility_id: str = Field(
        description="Facility identifier (e.g. watchtower, alchemical_workshop)"
    )
    outpost_id: str = Field(default="", description="Target outpost ID")
    gold_spent: int = Field(default=50, ge=0, description="Gold invested in upgrade")
    materials_spent: dict[str, int] = Field(
        default_factory=dict, description="Materials invested in upgrade"
    )


class PostNoticePayload(BaseModel):
    """Payload to post an expedition bounty, rumor, or request to the tavern notice board."""

    author_name: str = Field(description="Author character or NPC name")
    title: str = Field(description="Notice headline")
    content: str = Field(description="Body of the notice or rumor")
    notice_type: str = Field(default="bounty", description="Category: bounty, rumor, request")
    bounty_reward: int | str = Field(default=0, description="Bounty reward in gold or description")


class LinkSharedWorldPayload(BaseModel):
    """Payload to configure or link campaign to a West Marches shared frontier."""

    shared_world_id: str = Field(description="Shared world UUID or identifier")
    world_name: str = Field(default="The Frontier Marches", description="Shared world title")
    frontier_region: str = Field(default="The Untamed Wilds", description="Frontier region name")
    party_name: str = Field(default="Pioneers", description="Adventuring party name")
    description: str = Field(default="", description="World description")


@router.get("", response_model=WestMarchesState)
async def get_west_marches_overview(
    campaign_id: UUID,
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
    repo: Annotated[AggregateRepository[WestMarchesAtlasAggregate], Depends(get_west_marches_repo)],
    discovery_type: str | None = Query(default=None),
) -> WestMarchesState:
    """Retrieve shared frontier discoveries, communal stronghold dashboard, and tavern board."""
    can_view = await check_user_can_view_campaign(user_id, campaign_id, spicedb)
    if not can_view:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: User lacks view permission on campaign.",
        )

    try:
        aggregate = await repo.load(campaign_id)
    except Exception:
        aggregate = WestMarchesAtlasAggregate(campaign_id)
        await repo.save(aggregate)

    state = aggregate.state.model_copy()
    if discovery_type:
        state.discoveries = [
            d for d in state.discoveries if d.get("discovery_type") == discovery_type
        ]
    return state


@router.post("/link-world", response_model=WestMarchesState)
async def link_shared_world(
    campaign_id: UUID,
    payload: LinkSharedWorldPayload,
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
    repo: Annotated[AggregateRepository[WestMarchesAtlasAggregate], Depends(get_west_marches_repo)],
) -> WestMarchesState:
    """Link campaign to a shared world frontier or set world properties."""
    can_play = await check_user_can_play_campaign(user_id, campaign_id, spicedb)
    if not can_play:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: User lacks permission to configure campaign world.",
        )

    try:
        aggregate = await repo.load(campaign_id)
    except Exception:
        aggregate = WestMarchesAtlasAggregate(campaign_id)

    from runefoble_events.west_marches import (
        CampaignRegisteredToSharedWorld,
        SharedWorldCreated,
    )

    wid = payload.shared_world_id
    aggregate.create_event(
        SharedWorldCreated,
        shared_world_id=wid,
        name=payload.world_name,
        frontier_region=payload.frontier_region,
        description=payload.description,
        created_by=user_id or "system",
    )
    aggregate.create_event(
        CampaignRegisteredToSharedWorld,
        shared_world_id=wid,
        campaign_id=str(campaign_id),
        party_name=payload.party_name,
        registered_by=user_id or "system",
    )
    await repo.save(aggregate)
    return aggregate.state


@router.post("/discoveries", status_code=status.HTTP_201_CREATED)
async def record_discovery_pin(
    campaign_id: UUID,
    payload: RecordDiscoveryPayload,
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
    repo: Annotated[AggregateRepository[WestMarchesAtlasAggregate], Depends(get_west_marches_repo)],
) -> dict[str, Any]:
    """Record an expedition milestone pin in the shared frontier atlas."""
    can_play = await check_user_can_play_campaign(user_id, campaign_id, spicedb)
    if not can_play:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: User lacks discover/play permission on campaign.",
        )

    try:
        aggregate = await repo.load(campaign_id)
    except Exception:
        aggregate = WestMarchesAtlasAggregate(campaign_id)

    did = aggregate.record_discovery(
        name=payload.name,
        discovery_type=payload.discovery_type,
        coordinates=payload.coordinates,
        discovered_by_campaign_id=campaign_id,
        discovered_by_party_name=payload.discovered_by_party_name,
        description=payload.description,
        danger_level=payload.danger_level,
        discovery_id=payload.discovery_id,
        metadata=payload.metadata,
    )
    await repo.save(aggregate)

    found = next((d for d in aggregate.state.discoveries if d["discovery_id"] == did), None)
    return {"status": "created", "discovery": found}


@router.post("/stronghold/upgrade", status_code=status.HTTP_200_OK)
async def upgrade_stronghold_facility(
    campaign_id: UUID,
    payload: UpgradeStrongholdPayload,
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
    repo: Annotated[AggregateRepository[WestMarchesAtlasAggregate], Depends(get_west_marches_repo)],
) -> dict[str, Any]:
    """Upgrade a communal outpost facility and recalculate shared rest boons."""
    can_play = await check_user_can_play_campaign(user_id, campaign_id, spicedb)
    if not can_play:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: User lacks permission to upgrade stronghold facilities.",
        )

    try:
        aggregate = await repo.load(campaign_id)
    except Exception:
        aggregate = WestMarchesAtlasAggregate(campaign_id)

    outpost_id = payload.outpost_id
    if not outpost_id and aggregate.state.outposts:
        outpost_id = next(iter(aggregate.state.outposts.keys()))

    new_tier = aggregate.upgrade_outpost(
        outpost_id=outpost_id,
        facility_id=payload.facility_id,
        contributing_campaign_id=campaign_id,
        gold_spent=payload.gold_spent,
        materials_spent=payload.materials_spent,
    )
    await repo.save(aggregate)

    outpost = aggregate.state.outposts.get(outpost_id, {})
    return {
        "status": "upgraded",
        "facility_id": payload.facility_id,
        "new_tier": new_tier,
        "outpost": outpost,
        "active_boons": outpost.get("boons", []),
        "defensive_buffer": outpost.get("defensive_buffer", 0),
    }


@router.post("/tavern-board/notices", status_code=status.HTTP_201_CREATED)
async def post_tavern_notice(
    campaign_id: UUID,
    payload: PostNoticePayload,
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    spicedb: Annotated[SpiceDBClient, Depends(get_spicedb_client)],
    repo: Annotated[AggregateRepository[WestMarchesAtlasAggregate], Depends(get_west_marches_repo)],
) -> dict[str, Any]:
    """Post an expedition bounty, request, or rumor to the communal tavern notice board."""
    can_play = await check_user_can_play_campaign(user_id, campaign_id, spicedb)
    if not can_play:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: User lacks permission to post tavern notices.",
        )

    try:
        aggregate = await repo.load(campaign_id)
    except Exception:
        aggregate = WestMarchesAtlasAggregate(campaign_id)

    nid = aggregate.post_communal_notice(
        campaign_id=campaign_id,
        author_name=payload.author_name,
        title=payload.title,
        content=payload.content,
        notice_type=payload.notice_type,
        bounty_reward=payload.bounty_reward,
    )
    await repo.save(aggregate)

    found = next((n for n in aggregate.state.tavern_board if n["notice_id"] == nid), None)
    return {"status": "posted", "notice": found}
