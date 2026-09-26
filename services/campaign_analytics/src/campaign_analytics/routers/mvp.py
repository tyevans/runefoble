"""Combat MVP turn statistics and performance award analytics router."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Query

from campaign_analytics.dependencies import SpiceDep, StorageDep, check_user_can_view_campaign
from campaign_analytics.models import CampaignMvpResponse

router = APIRouter(prefix="/api/v1/analytics/campaigns", tags=["Combat Performance & MVP"])


@router.get(
    "/{id}/mvp",
    response_model=CampaignMvpResponse,
    summary="Get encounter MVP awards and combat statistics",
    description="Per-encounter and per-campaign MVP awards based on damage dealt, healing, and critical strikes.",
)
async def get_campaign_mvp(
    id: str,
    storage: StorageDep,
    spicedb: SpiceDep,
    session_id: Annotated[str | None, Query(description="Filter by specific session ID")] = None,
    encounter_id: Annotated[
        str | None, Query(description="Filter by specific encounter ID")
    ] = None,
    x_user_id: Annotated[str | None, Header(alias="X-User-ID")] = None,
) -> CampaignMvpResponse:
    """Retrieve combatant MVP rankings and tactical awards."""
    can_view = await check_user_can_view_campaign(x_user_id, id, spicedb)
    if not can_view:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: User lacks permission to view campaign analytics",
        )

    return await storage.get_mvp(
        campaign_id=id,
        session_id=session_id,
        encounter_id=encounter_id,
    )
