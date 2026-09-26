"""Tactical spatial heatmap and damage density analytics router."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Query

from campaign_analytics.dependencies import SpiceDep, StorageDep, check_user_can_view_campaign
from campaign_analytics.models import CampaignHeatmapResponse

router = APIRouter(prefix="/api/v1/analytics/campaigns", tags=["Combat Spatial Heatmaps"])


@router.get(
    "/{id}/heatmap",
    response_model=CampaignHeatmapResponse,
    summary="Get tactical spatial heatmap",
    description="Aggregated spatial coordinate hit/damage densities and token traffic patterns.",
)
async def get_campaign_heatmap(
    id: str,
    storage: StorageDep,
    spicedb: SpiceDep,
    session_id: Annotated[str | None, Query(description="Filter by specific session ID")] = None,
    cell_size: Annotated[int, Query(ge=1, le=50, description="Spatial bucketing granularity")] = 5,
    metric: Annotated[
        str, Query(description="Heatmap metric type: 'all', 'damage', 'hit', 'movement'")
    ] = "all",
    x_user_id: Annotated[str | None, Header(alias="X-User-ID")] = None,
) -> CampaignHeatmapResponse:
    """Retrieve spatial heatmap density matrices."""
    can_view = await check_user_can_view_campaign(x_user_id, id, spicedb)
    if not can_view:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: User lacks permission to view campaign analytics",
        )

    return await storage.get_heatmap(
        campaign_id=id,
        session_id=session_id,
        cell_size=cell_size,
        metric=metric,
    )
