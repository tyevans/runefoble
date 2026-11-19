"""FastAPI APIRouter and FastMCP tools for settlements and frontier havens.

Part of TASK-0164 / PRD-0018 / US-0058 / ADR-0001 / ADR-0006 / ADR-0011.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from game_session.dependencies import get_event_bus, get_settlement_repository
from game_session.events import STREAM_WEST_MARCHES
from game_session.settlement.auth import (
    check_settlement_permission,
    check_world_charter_permission,
    register_campaign_haven_discovery,
    write_settlement_relationships,
)
from game_session.settlement.auth.tokens import CallerId, get_principal
from game_session.settlement.facility_prices import InsufficientSettlementResources
from game_session.settlement.models import (
    CharterSettlementRequest,
    ClaimRestBoonRequest,
    DepositSettlementRequest,
    UpgradeFacilityRequest,
)
from game_session.settlement.settlement_aggregate import SettlementAggregate
from runefoble_auth.factory import get_spicedb_client
from runefoble_platform.event_publish import publish_or_fail
from runefoble_platform.identifiers import parse_uuid

router = APIRouter(
    dependencies=[Depends(get_principal)], prefix="/settlements", tags=["settlements"]
)


async def _save_and_publish(repo: Any, bus: Any, agg: Any) -> None:
    events = list(agg.uncommitted_events)
    await repo.save(agg)
    if bus:
        for ev in events:
            await publish_or_fail(bus, STREAM_WEST_MARCHES, ev)


async def _load_haven(sid: str, perm: str, uid: str | None) -> SettlementAggregate:
    settlement_uuid = parse_uuid(sid, field="settlement_id")
    try:
        agg = await get_settlement_repository().load(settlement_uuid)
    except Exception as e:
        raise HTTPException(status_code=404, detail="Settlement not found") from e
    await check_settlement_permission(get_spicedb_client(), sid, perm, uid)
    return agg


@router.post("", status_code=201)
async def charter_settlement(
    caller_id: CallerId,
    req: CharterSettlementRequest,
) -> dict[str, Any]:
    """Charter a new persistent communal haven or outpost in a shared world."""
    spicedb, repo, bus = get_spicedb_client(), get_settlement_repository(), get_event_bus()
    await check_world_charter_permission(spicedb, req.shared_world_id, caller_id)
    sid = uuid4()
    agg = SettlementAggregate(sid)
    agg.charter(
        name=req.name,
        shared_world_id=req.shared_world_id,
        settlement_type=req.settlement_type,
        region=req.region,
        coordinates=req.coordinates,
        founded_by_campaign_id=req.founded_by_campaign_id,
        chartered_by=caller_id,
        facilities=req.facilities,
        defense_rating=req.defense_rating,
        metadata=req.metadata,
    )
    await _save_and_publish(repo, bus, agg)
    await write_settlement_relationships(
        spicedb,
        str(sid),
        campaign_id=req.founded_by_campaign_id,
        founder_id=caller_id,
        shared_world_id=req.shared_world_id,
    )
    return {"settlement_id": str(sid), **agg.state.model_dump()}


@router.get("/{settlement_id}")
async def get_settlement(
    caller_id: CallerId,
    settlement_id: str,
) -> dict[str, Any]:
    """Query settlement state, fortification ratings, and facility tiers."""
    agg = await _load_haven(settlement_id, "view", caller_id)
    return {"settlement_id": str(settlement_id), **agg.state.model_dump()}


@router.post("/{settlement_id}/upgrade")
async def upgrade_settlement(
    caller_id: CallerId,
    settlement_id: str,
    req: UpgradeFacilityRequest,
) -> dict[str, Any]:
    """Upgrade workshop, resting sanctum, or fortifications tier."""
    agg = await _load_haven(settlement_id, "upgrade", caller_id)
    try:
        tier = agg.upgrade_facility(req.facility_id, req.contributing_campaign_id)
    except InsufficientSettlementResources as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
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


@router.post("/{settlement_id}/deposit")
async def deposit_haven_resources(
    caller_id: CallerId,
    settlement_id: str,
    req: DepositSettlementRequest,
) -> dict[str, Any]:
    """Add gold and materials to the haven treasury. Only a manager may fund a haven."""
    agg = await _load_haven(settlement_id, "manage", caller_id)
    try:
        agg.deposit_resources(gold=req.gold, materials=req.materials, deposited_by=caller_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await _save_and_publish(get_settlement_repository(), get_event_bus(), agg)
    return {"settlement_id": str(settlement_id), **agg.state.model_dump()}


@router.post("/{settlement_id}/claim-boon")
async def claim_haven_rest_boon(
    caller_id: CallerId,
    settlement_id: str,
    req: ClaimRestBoonRequest,
) -> dict[str, Any]:
    """Claim sanctum resting boons or workshop buffs for an adventuring party."""
    agg = await _load_haven(settlement_id, "use", caller_id)
    boon = agg.claim_rest_boon(req.campaign_id, req.character_id, caller_id, req.facility_id)
    await _save_and_publish(get_settlement_repository(), get_event_bus(), agg)
    return {"settlement_id": str(settlement_id), "boon": boon, **agg.state.model_dump()}


def register_settlement_mcp_tools(mcp: Any) -> None:
    """Register frontier settlement tools on FastMCP gateway."""
    mcp.tool()(charter_settlement)
    mcp.tool()(get_settlement)
    mcp.tool()(upgrade_settlement)
