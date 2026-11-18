"""FastAPI APIRouter for party campsite and stronghold upgrades.

Part of TASK-0100 / PRD-0014 / US-0044.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from eventsource import AggregateNotFoundError
from fastapi import APIRouter, Depends, HTTPException
from game_session.dependencies import get_event_bus, get_spicedb_client, stronghold_repo
from game_session.events import STREAM_STRONGHOLD
from game_session.settlement.auth.tokens import CallerId, get_caller_principal
from game_session.stronghold import (
    FACILITY_TIERS,
    InsufficientStrongholdResources,
    StrongholdAggregate,
    StrongholdState,
)
from pydantic import BaseModel, ConfigDict, Field
from runefoble_platform.event_publish import publish_or_fail

router = APIRouter(dependencies=[Depends(get_caller_principal)], tags=["stronghold"])


def _camp_uuid(campaign_id: str) -> UUID | str:
    return (
        UUID(campaign_id)
        if isinstance(campaign_id, str) and len(campaign_id) == 36
        else campaign_id
    )


async def _require(spicedb: Any, resource: str, rid: str, perm: str, uid: str, detail: str) -> None:
    """Deny unless the verified caller holds `perm` on the resource (schema name only)."""
    if not await spicedb.check_permission(resource, rid, perm, "user", uid):
        raise HTTPException(status_code=403, detail=detail)


async def _link_stronghold(spicedb: Any, campaign_id: str) -> None:
    """Bind the stronghold object to its campaign so `stronghold.upgrade` can resolve."""
    await spicedb.touch_relationship("stronghold", campaign_id, "campaign", "campaign", campaign_id)


class UpgradeStrongholdRequest(BaseModel):
    """Names the facility only. The tier table sets the cost, so extra fields answer 422."""

    model_config = ConfigDict(extra="forbid")

    facility_id: str


class UpgradeStrongholdResponse(BaseModel):
    campaign_id: str
    facility_id: str
    new_tier: int
    tier_name: str
    gold_spent: int
    materials_spent: dict[str, int]
    unlocked_boon: str
    state: StrongholdState


class DepositStrongholdRequest(BaseModel):
    gold: int = 0
    materials: dict[str, int] = Field(default_factory=dict)


class ContributeTreasuryRequest(BaseModel):
    """Gold that leaves the treasury to fund a frontier outpost (TASK-0795).

    The destination id is recorded for the audit trail. This service does not read it.
    """

    model_config = ConfigDict(extra="forbid")

    gold: int = Field(gt=0)
    destination_outpost_id: str = ""


class CreateStrongholdRequest(BaseModel):
    name: str = "Party Campsite"
    location: str = "Wilderness"


@router.get("/api/v1/campaigns/{campaign_id}/stronghold", response_model=StrongholdState)
async def get_stronghold(caller_id: CallerId, campaign_id: str) -> StrongholdState:
    """Retrieve party stronghold / campsite status and facility tiers."""
    await _require(
        get_spicedb_client(), "campaign", campaign_id, "view", caller_id, "Campaign view required"
    )
    try:
        stronghold = await stronghold_repo.load(_camp_uuid(campaign_id))
    except AggregateNotFoundError:
        # Return default initialized state if none exists yet
        return StrongholdState(campaign_id=str(campaign_id))
    return stronghold.state


@router.post("/api/v1/campaigns/{campaign_id}/stronghold", response_model=StrongholdState)
async def initialize_stronghold(
    caller_id: CallerId,
    campaign_id: str,
    req: CreateStrongholdRequest,
) -> StrongholdState:
    """Initialize or rename party stronghold / campsite."""
    spicedb = get_spicedb_client()
    await _require(
        spicedb,
        "campaign",
        campaign_id,
        "run_session",
        caller_id,
        "DM or owner permission required",
    )
    camp_uuid = _camp_uuid(campaign_id)
    try:
        stronghold = await stronghold_repo.load(camp_uuid)
    except AggregateNotFoundError:
        stronghold = StrongholdAggregate(camp_uuid)

    stronghold.create_stronghold(campaign_id=str(campaign_id), name=req.name, location=req.location)
    await stronghold_repo.save(stronghold)
    await _link_stronghold(spicedb, str(campaign_id))
    return stronghold.state


async def _load_or_start_stronghold(
    spicedb: Any, campaign_id: str, caller_id: str, detail: str
) -> StrongholdAggregate:
    """Load the campsite. A new campsite needs a campaign player, and the link lets it resolve."""
    camp_uuid = _camp_uuid(campaign_id)
    try:
        return await stronghold_repo.load(camp_uuid)
    except AggregateNotFoundError:
        await _require(spicedb, "campaign", campaign_id, "play", caller_id, detail)
        stronghold = StrongholdAggregate(camp_uuid)
        stronghold.create_stronghold(campaign_id=str(campaign_id))
        await _link_stronghold(spicedb, str(campaign_id))
        return stronghold


@router.post("/api/v1/campaigns/{campaign_id}/stronghold/deposit", response_model=StrongholdState)
async def deposit_stronghold_resources(
    caller_id: CallerId,
    campaign_id: str,
    req: DepositStrongholdRequest,
) -> StrongholdState:
    """Add gold and materials to the campsite treasury and material store.

    A deposit creates resources, so only a DM or stronghold manager (`manage`) may make one.
    """
    spicedb = get_spicedb_client()
    detail = "DM permission required to fund campsite"
    stronghold = await _load_or_start_stronghold(spicedb, campaign_id, caller_id, detail)
    await _require(spicedb, "stronghold", campaign_id, "manage", caller_id, detail)
    try:
        stronghold.deposit_resources(gold=req.gold, materials=req.materials)
        events_to_publish = list(stronghold.uncommitted_events)
        await stronghold_repo.save(stronghold)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    bus = get_event_bus()
    if bus:
        for ev in events_to_publish:
            await publish_or_fail(bus, STREAM_STRONGHOLD, ev)
    return stronghold.state


@router.post(
    "/api/v1/campaigns/{campaign_id}/stronghold/upgrade", response_model=UpgradeStrongholdResponse
)
async def upgrade_stronghold_facility(
    caller_id: CallerId,
    campaign_id: str,
    req: UpgradeStrongholdRequest,
) -> UpgradeStrongholdResponse:
    """Upgrade campsite/stronghold facility, consuming gold/materials and granting resting boons."""
    spicedb = get_spicedb_client()
    detail = "Player or DM permission required to upgrade campsite"
    stronghold = await _load_or_start_stronghold(spicedb, campaign_id, caller_id, detail)
    await _require(spicedb, "stronghold", campaign_id, "upgrade", caller_id, detail)

    try:
        upgrade_result = stronghold.upgrade_facility(facility_id=req.facility_id)
        events_to_publish = list(stronghold.uncommitted_events)
        await stronghold_repo.save(stronghold)
    except InsufficientStrongholdResources as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Publish events to Redis Streams
    bus = get_event_bus()
    if bus:
        for ev in events_to_publish:
            await publish_or_fail(bus, STREAM_STRONGHOLD, ev)

    return UpgradeStrongholdResponse(
        campaign_id=str(campaign_id),
        facility_id=upgrade_result["facility_id"],
        new_tier=upgrade_result["new_tier"],
        tier_name=upgrade_result["tier_name"],
        gold_spent=upgrade_result["gold_spent"],
        materials_spent=upgrade_result["materials_spent"],
        unlocked_boon=upgrade_result["unlocked_boon"],
        state=stronghold.state,
    )


@router.get("/api/v1/campaigns/{campaign_id}/stronghold/boons")
async def get_stronghold_boons(caller_id: CallerId, campaign_id: str) -> dict[str, Any]:
    """Retrieve active party rest bonuses granted by camp facilities."""
    await _require(
        get_spicedb_client(), "campaign", campaign_id, "view", caller_id, "Campaign view required"
    )
    try:
        stronghold = await stronghold_repo.load(_camp_uuid(campaign_id))
    except AggregateNotFoundError:
        return {"campaign_id": campaign_id, "active_boons": [], "catalog": FACILITY_TIERS}
    boons = stronghold.get_active_boons()
    return {"campaign_id": campaign_id, "active_boons": boons, "catalog": FACILITY_TIERS}


__all__ = ["router"]


@router.post(
    "/api/v1/campaigns/{campaign_id}/stronghold/treasury/contribute",
    response_model=StrongholdState,
)
async def contribute_treasury_gold(
    caller_id: CallerId,
    campaign_id: str,
    req: ContributeTreasuryRequest,
) -> StrongholdState:
    """Debit gold from the treasury for a frontier outpost. `stronghold.manage` is required.

    A shortfall answers 409 and records no event. A campaign with no campsite has an empty
    treasury, so any positive amount is a shortfall.
    """
    spicedb = get_spicedb_client()
    detail = "DM or stronghold manager permission required to contribute treasury gold"
    await _require(spicedb, "stronghold", campaign_id, "manage", caller_id, detail)
    camp_uuid = _camp_uuid(campaign_id)
    try:
        stronghold = await stronghold_repo.load(camp_uuid)
    except AggregateNotFoundError:
        stronghold = StrongholdAggregate(camp_uuid)

    try:
        stronghold.contribute_treasury_gold(
            gold=req.gold, destination_outpost_id=req.destination_outpost_id
        )
        events_to_publish = list(stronghold.uncommitted_events)
        await stronghold_repo.save(stronghold)
    except InsufficientStrongholdResources as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    bus = get_event_bus()
    if bus:
        for ev in events_to_publish:
            await publish_or_fail(bus, STREAM_STRONGHOLD, ev)
    return stronghold.state
