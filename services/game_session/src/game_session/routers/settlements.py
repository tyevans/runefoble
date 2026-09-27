"""FastAPI APIRouter and FastMCP tools for settlements and frontier havens.

Part of TASK-0164 / PRD-0018 / US-0058 / ADR-0001 / ADR-0006 / ADR-0011.
"""

from __future__ import annotations

import contextlib
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, HTTPException
from game_session.dependencies import (
    STREAM_WEST_MARCHES,
    get_event_bus,
    get_settlement_repository,
    get_spicedb_client,
)
from game_session.settlements import (
    CharterSettlementRequest,
    ClaimRestBoonRequest,
    SettlementAggregate,
    UpgradeFacilityRequest,
    check_settlement_permission,
    check_world_charter_permission,
    register_campaign_haven_discovery,
    write_settlement_relationships,
)

router = APIRouter(prefix="/settlements", tags=["settlements"])


def _to_uuid(val: Any) -> UUID:
    try:
        return val if isinstance(val, UUID) else UUID(str(val))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {val}") from e


async def _save_and_publish(repo: Any, bus: Any, agg: Any) -> None:
    events = list(agg.uncommitted_events)
    await repo.save(agg)
    if bus:
        for ev in events:
            with contextlib.suppress(Exception):
                await bus.publish_event(STREAM_WEST_MARCHES, ev)


async def _load_haven(sid: str, perm: str, uid: str | None) -> SettlementAggregate:
    try:
        agg = await get_settlement_repository().load(_to_uuid(sid))
    except Exception as e:
        raise HTTPException(status_code=404, detail="Settlement not found") from e
    await check_settlement_permission(get_spicedb_client(), sid, perm, uid)
    return agg


@router.post("", status_code=201)
async def charter_settlement(
    req: CharterSettlementRequest,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    """Charter a new persistent communal haven or outpost in a shared world."""
    spicedb, repo, bus = get_spicedb_client(), get_settlement_repository(), get_event_bus()
    await check_world_charter_permission(spicedb, req.shared_world_id, x_user_id)
    sid = uuid4()
    agg = SettlementAggregate(sid)
    agg.charter(
        name=req.name,
        shared_world_id=req.shared_world_id,
        settlement_type=req.settlement_type,
        region=req.region,
        coordinates=req.coordinates,
        founded_by_campaign_id=req.founded_by_campaign_id,
        chartered_by=x_user_id or "system",
        facilities=req.facilities,
        defense_rating=req.defense_rating,
        metadata=req.metadata,
    )
    await _save_and_publish(repo, bus, agg)
    await write_settlement_relationships(
        spicedb, str(sid), req.shared_world_id, x_user_id, req.founded_by_campaign_id
    )
    return {"settlement_id": str(sid), **agg.state.model_dump()}


@router.get("/{settlement_id}")
async def get_settlement(
    settlement_id: str,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    """Query settlement state, fortification ratings, and facility tiers."""
    agg = await _load_haven(settlement_id, "view", x_user_id)
    return {"settlement_id": str(settlement_id), **agg.state.model_dump()}


@router.post("/{settlement_id}/upgrade")
async def upgrade_settlement(
    settlement_id: str,
    req: UpgradeFacilityRequest,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    """Upgrade workshop, resting sanctum, or fortifications tier."""
    agg = await _load_haven(settlement_id, "upgrade", x_user_id)
    tier = agg.upgrade_facility(
        req.facility_id, req.contributing_campaign_id, req.gold_spent, req.materials_spent
    )
    await _save_and_publish(get_settlement_repository(), get_event_bus(), agg)
    if req.contributing_campaign_id:
        await register_campaign_haven_discovery(
            get_spicedb_client(), settlement_id, req.contributing_campaign_id
        )
    return {
        "settlement_id": str(settlement_id),
        "facility_id": req.facility_id,
        "new_tier": tier,
        **agg.state.model_dump(),
    }


@router.post("/{settlement_id}/claim-boon")
async def claim_haven_rest_boon(
    settlement_id: str,
    req: ClaimRestBoonRequest,
    x_user_id: str | None = Header(default=None),
) -> dict[str, Any]:
    """Claim sanctum resting boons or workshop buffs for an adventuring party."""
    agg = await _load_haven(settlement_id, "use", x_user_id)
    boon = agg.claim_rest_boon(req.campaign_id, req.character_id, x_user_id or "", req.facility_id)
    await _save_and_publish(get_settlement_repository(), get_event_bus(), agg)
    return {"settlement_id": str(settlement_id), "boon": boon, **agg.state.model_dump()}


def register_settlement_mcp_tools(mcp: Any) -> None:
    """Register frontier settlement tools on FastMCP gateway."""
    mcp.tool()(charter_settlement)
    mcp.tool()(get_settlement)
    mcp.tool()(upgrade_settlement)
