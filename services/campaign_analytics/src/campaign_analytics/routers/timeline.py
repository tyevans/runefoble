"""Campaign chronicle milestone timeline analytics router."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from campaign_analytics.dependencies import (
    CurrentUserId,
    SpiceDep,
    StorageDep,
    check_user_can_view_campaign,
    get_current_user_id,
)
from campaign_analytics.models import CampaignTimelineResponse

router = APIRouter(
    prefix="/api/v1/analytics/campaigns",
    tags=["Chronicle Milestone Timeline"],
    dependencies=[Depends(get_current_user_id)],
)


@router.get(
    "/{id}/timeline",
    response_model=CampaignTimelineResponse,
    summary="Get campaign chronicle milestone timeline",
    description="Chronological event milestones linking session recaps, boss encounters, and pivotal moments.",
)
async def get_campaign_timeline(
    id: str,
    storage: StorageDep,
    spicedb: SpiceDep,
    user_id: CurrentUserId,
    session_id: Annotated[str | None, Query(description="Filter by specific session ID")] = None,
    limit: Annotated[int, Query(ge=1, le=500, description="Max milestones to return")] = 50,
) -> CampaignTimelineResponse:
    """Retrieve chronological session and combat milestones."""
    can_view = await check_user_can_view_campaign(user_id, id, spicedb)
    if not can_view:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: User lacks permission to view campaign analytics",
        )

    return await storage.get_timeline(
        campaign_id=id,
        session_id=session_id,
        limit=limit,
    )
