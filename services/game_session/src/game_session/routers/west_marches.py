"""FastAPI APIRouter for West Marches shared frontier, discoveries, and tavern notice board.

Part of TASK-0127 / PRD-0007 / US-0058 / ADR-0001 / ADR-0006 / ADR-0011.
Governed by Hard Invariant 1 (SpiceDB Zanzibar) and Hard Invariant 2 (eventsource-py).
"""

from __future__ import annotations

import contextlib
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, HTTPException, Query
from game_session.dependencies import (
    STREAM_WEST_MARCHES,
    get_event_bus,
    get_shared_world_repository,
    get_spicedb_client,
)
from game_session.west_marches_models import (
    CreateSharedWorldRequest,
    EstablishOutpostRequest,
    PostNoticeRequest,
    RecordDiscoveryRequest,
    RegisterCampaignRequest,
)

router = APIRouter(prefix="/api/v1/shared-worlds", tags=["west-marches"])


def _to_uuid(val: Any) -> UUID:
    if isinstance(val, UUID):
        return val
    try:
        return UUID(str(val))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {val}") from e


async def _check_perm(spicedb, res_id: str, perm: str, user_id: str | None) -> None:
    if user_id and not await spicedb.check_permission(
        "shared_world", str(res_id), perm, "user", user_id
    ):
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: subject '{user_id}' lacks '{perm}' on shared_world:{res_id}",
        )


@router.post("", status_code=201)
async def create_shared_world(
    req: CreateSharedWorldRequest,
    x_user_id: str | None = Header(default="guild_officer_rowan"),
) -> dict[str, Any]:
    """Create a new West Marches shared frontier persistent world."""
    world_id = uuid4()
    repo = get_shared_world_repository()
    spicedb = get_spicedb_client()

    from game_session.west_marches import SharedWorldAggregate

    world = SharedWorldAggregate(world_id)
    world.create_shared_world(
        name=req.name,
        frontier_region=req.frontier_region,
        description=req.description,
        created_by=x_user_id or "system",
    )
    await repo.save(world)

    if x_user_id:
        await spicedb.write_relationship(
            resource_type="shared_world",
            resource_id=str(world_id),
            relation="guild_officer",
            subject_type="user",
            subject_id=x_user_id,
        )

    return {"shared_world_id": str(world_id), **world.state.model_dump()}


@router.get("/{shared_world_id}")
async def get_shared_world(
    shared_world_id: str,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    """Retrieve shared frontier world state (discoveries, outposts, tavern notices)."""
    wid = _to_uuid(shared_world_id)
    spicedb = get_spicedb_client()
    await _check_perm(spicedb, str(wid), "view", x_user_id)

    repo = get_shared_world_repository()
    try:
        world = await repo.load(wid)
    except Exception as e:
        raise HTTPException(status_code=404, detail="Shared world not found") from e
    return {"shared_world_id": str(wid), **world.state.model_dump()}


@router.post("/{shared_world_id}/campaigns", status_code=201)
async def register_campaign_to_world(
    shared_world_id: str,
    req: RegisterCampaignRequest,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    """Register an adventuring campaign/party into the shared persistent frontier."""
    wid = _to_uuid(shared_world_id)
    repo = get_shared_world_repository()
    spicedb = get_spicedb_client()

    world = await repo.load(wid)
    world.register_campaign(
        campaign_id=req.campaign_id,
        party_name=req.party_name,
        registered_by=x_user_id or "guild_officer",
    )
    await repo.save(world)

    await spicedb.write_relationship(
        resource_type="shared_world",
        resource_id=str(wid),
        relation="campaign",
        subject_type="campaign",
        subject_id=str(req.campaign_id),
    )

    return {
        "shared_world_id": str(wid),
        "campaign_id": str(req.campaign_id),
        "party_name": req.party_name,
        "status": "registered",
    }


@router.post("/{shared_world_id}/discoveries", status_code=201)
async def record_discovery(
    shared_world_id: str,
    req: RecordDiscoveryRequest,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    """Record a cross-campaign milestone / waypoint discovery and broadcast on Redis Streams."""
    wid = _to_uuid(shared_world_id)
    spicedb = get_spicedb_client()
    await _check_perm(spicedb, str(wid), "discover", x_user_id)

    repo = get_shared_world_repository()
    world = await repo.load(wid)
    did = world.record_discovery(
        name=req.name,
        discovery_type=req.discovery_type,
        coordinates=req.coordinates,
        discovered_by_campaign_id=req.discovered_by_campaign_id,
        discovered_by_party_name=req.discovered_by_party_name,
        description=req.description,
        danger_level=req.danger_level,
        discovery_id=req.discovery_id,
        metadata=req.metadata,
    )
    events_to_emit = list(world.uncommitted_events)
    await repo.save(world)

    bus = get_event_bus()
    if bus:
        for ev in events_to_emit:
            with contextlib.suppress(Exception):
                await bus.publish_event(STREAM_WEST_MARCHES, ev)

    found = next((d for d in world.state.discoveries if d["discovery_id"] == did), None)
    return {"shared_world_id": str(wid), "discovery": found}


@router.get("/{shared_world_id}/discoveries")
async def list_discoveries(
    shared_world_id: str,
    discovery_type: str | None = Query(default=None),
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    """List shared frontier discoveries mapped by participating adventuring parties."""
    wid = _to_uuid(shared_world_id)
    spicedb = get_spicedb_client()
    await _check_perm(spicedb, str(wid), "view", x_user_id)

    repo = get_shared_world_repository()
    world = await repo.load(wid)
    results = world.state.discoveries
    if discovery_type:
        results = [d for d in results if d["discovery_type"] == discovery_type]
    return {"shared_world_id": str(wid), "discoveries": results}


@router.post("/{shared_world_id}/outposts", status_code=201)
async def establish_outpost(
    shared_world_id: str,
    req: EstablishOutpostRequest,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    """Establish or reinforce a regional trading outpost in the frontier."""
    wid = _to_uuid(shared_world_id)
    spicedb = get_spicedb_client()
    await _check_perm(spicedb, str(wid), "discover", x_user_id)

    repo = get_shared_world_repository()
    world = await repo.load(wid)
    oid = world.establish_outpost(
        name=req.name,
        region=req.region,
        contributing_campaign_id=req.contributing_campaign_id,
        outpost_id=req.outpost_id,
        facilities=req.facilities,
        resources_contributed=req.resources_contributed,
    )
    await repo.save(world)
    return {"shared_world_id": str(wid), "outpost": world.state.outposts[oid]}


@router.post("/{shared_world_id}/tavern-board/notices", status_code=201)
async def post_tavern_notice(
    shared_world_id: str,
    req: PostNoticeRequest,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    """Post an expedition bounty, request, or rumor to the communal tavern notice board."""
    wid = _to_uuid(shared_world_id)
    spicedb = get_spicedb_client()
    await _check_perm(spicedb, str(wid), "discover", x_user_id)

    repo = get_shared_world_repository()
    world = await repo.load(wid)
    nid = world.post_communal_notice(
        campaign_id=req.campaign_id,
        author_name=req.author_name,
        title=req.title,
        content=req.content,
        notice_type=req.notice_type,
        bounty_reward=req.bounty_reward,
    )
    await repo.save(world)
    notice = next((n for n in world.state.tavern_board if n["notice_id"] == nid), None)
    return {"shared_world_id": str(wid), "notice": notice}


@router.get("/{shared_world_id}/tavern-board/notices")
async def list_tavern_notices(
    shared_world_id: str,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    """List communal tavern notice board bounties and rumors across all campaigns."""
    wid = _to_uuid(shared_world_id)
    spicedb = get_spicedb_client()
    await _check_perm(spicedb, str(wid), "view", x_user_id)

    repo = get_shared_world_repository()
    world = await repo.load(wid)
    return {"shared_world_id": str(wid), "notices": world.state.tavern_board}
