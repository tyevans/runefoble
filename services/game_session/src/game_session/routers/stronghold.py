"""FastAPI APIRouter for party campsite and stronghold upgrades.

Part of TASK-0100 / PRD-0014 / US-0044.
"""

from __future__ import annotations

import contextlib
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException
from game_session.dependencies import (
    STREAM_STRONGHOLD,
    get_event_bus,
    get_spicedb_client,
    stronghold_repo,
)
from game_session.stronghold import (
    FACILITY_TIERS,
    StrongholdAggregate,
    StrongholdState,
)
from pydantic import BaseModel, Field

router = APIRouter(tags=["stronghold"])


class UpgradeStrongholdRequest(BaseModel):
    facility_id: str
    gold_spent: int = 0
    materials_spent: dict[str, int] = Field(default_factory=dict)


class UpgradeStrongholdResponse(BaseModel):
    campaign_id: str
    facility_id: str
    new_tier: int
    tier_name: str
    gold_spent: int
    materials_spent: dict[str, int]
    unlocked_boon: str
    state: StrongholdState


class CreateStrongholdRequest(BaseModel):
    name: str = "Party Campsite"
    location: str = "Wilderness"


@router.get("/api/v1/campaigns/{campaign_id}/stronghold", response_model=StrongholdState)
async def get_stronghold(campaign_id: str) -> StrongholdState:
    """Retrieve party stronghold / campsite status and facility tiers."""
    try:
        camp_uuid = (
            UUID(campaign_id)
            if isinstance(campaign_id, str) and len(campaign_id) == 36
            else campaign_id
        )
        stronghold = await stronghold_repo.load(camp_uuid)
        return stronghold.state
    except Exception:
        # Return default initialized state if none exists yet
        return StrongholdState(campaign_id=str(campaign_id))


@router.post("/api/v1/campaigns/{campaign_id}/stronghold", response_model=StrongholdState)
async def initialize_stronghold(
    campaign_id: str,
    req: CreateStrongholdRequest,
    x_user_id: str | None = Header(default=None),
) -> StrongholdState:
    """Initialize or rename party stronghold / campsite."""
    spicedb = get_spicedb_client()
    if x_user_id and not await spicedb.check_permission(
        "campaign", campaign_id, "run_session", "user", x_user_id
    ):
        raise HTTPException(status_code=403, detail="DM or owner permission required")

    camp_uuid = (
        UUID(campaign_id)
        if isinstance(campaign_id, str) and len(campaign_id) == 36
        else campaign_id
    )
    try:
        stronghold = await stronghold_repo.load(camp_uuid)
    except Exception:
        stronghold = StrongholdAggregate(camp_uuid)

    stronghold.create_stronghold(campaign_id=str(campaign_id), name=req.name, location=req.location)
    await stronghold_repo.save(stronghold)
    return stronghold.state


@router.post(
    "/api/v1/campaigns/{campaign_id}/stronghold/upgrade", response_model=UpgradeStrongholdResponse
)
async def upgrade_stronghold_facility(
    campaign_id: str,
    req: UpgradeStrongholdRequest,
    x_user_id: str | None = Header(default=None),
) -> UpgradeStrongholdResponse:
    """Upgrade campsite/stronghold facility, consuming gold/materials and granting resting boons."""
    spicedb = get_spicedb_client()
    if x_user_id and not await spicedb.check_permission(
        "campaign", campaign_id, "play", "user", x_user_id
    ):
        raise HTTPException(
            status_code=403, detail="Player or DM permission required to upgrade campsite"
        )

    camp_uuid = (
        UUID(campaign_id)
        if isinstance(campaign_id, str) and len(campaign_id) == 36
        else campaign_id
    )
    try:
        stronghold = await stronghold_repo.load(camp_uuid)
    except Exception:
        stronghold = StrongholdAggregate(camp_uuid)
        stronghold.create_stronghold(campaign_id=str(campaign_id))

    try:
        upgrade_result = stronghold.upgrade_facility(
            facility_id=req.facility_id,
            gold_spent=req.gold_spent,
            materials_spent=req.materials_spent or None,
        )
        events_to_publish = list(stronghold.uncommitted_events)
        await stronghold_repo.save(stronghold)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Publish events to Redis Streams
    bus = get_event_bus()
    if bus:
        for ev in events_to_publish:
            with contextlib.suppress(Exception):
                await bus.publish_event(STREAM_STRONGHOLD, ev)

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
async def get_stronghold_boons(campaign_id: str) -> dict[str, Any]:
    """Retrieve active party rest bonuses granted by camp facilities."""
    camp_uuid = (
        UUID(campaign_id)
        if isinstance(campaign_id, str) and len(campaign_id) == 36
        else campaign_id
    )
    try:
        stronghold = await stronghold_repo.load(camp_uuid)
        boons = stronghold.get_active_boons()
    except Exception:
        boons = []
    return {"campaign_id": campaign_id, "active_boons": boons, "catalog": FACILITY_TIERS}


__all__ = ["router"]
