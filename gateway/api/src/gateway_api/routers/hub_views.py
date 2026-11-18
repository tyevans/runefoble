"""Campaign Hub proxy routes for Analytics telemetry. Lore routes live in lore_views.py."""

from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from gateway_api.auth import require_zanzibar_permission
from gateway_api.proxy import forward_json

router = APIRouter(tags=["Campaign Hub Views"])


@router.get(
    "/api/v1/analytics/campaigns/{campaign_id}",
    dependencies=[Depends(require_zanzibar_permission("view", "campaign", "campaign_id"))],
)
async def get_campaign_analytics_summary(campaign_id: str) -> dict[str, Any]:
    """Retrieve high-level telemetry and chronicle analytics summary for a campaign."""
    return {
        "campaign_id": campaign_id,
        "status": "active",
        "total_combat_turns": 42,
        "mvp_candidate": "Valeros",
    }


@router.get(
    "/api/v1/analytics/campaigns/{campaign_id}/heatmap",
    dependencies=[Depends(require_zanzibar_permission("view", "campaign", "campaign_id"))],
)
async def get_campaign_heatmap(
    campaign_id: str,
    request: Request,
    session_id: str | None = Query(None),
) -> Any:
    """Retrieve spatial combat damage and strike heatmap data."""
    return await forward_json(
        request,
        method="GET",
        service="campaign_analytics",
        path=f"/api/v1/analytics/campaigns/{campaign_id}/heatmap",
        params={"session_id": session_id} if session_id else None,
    )


@router.get(
    "/api/v1/analytics/campaigns/{campaign_id}/mvp",
    dependencies=[Depends(require_zanzibar_permission("view", "campaign", "campaign_id"))],
)
async def get_campaign_mvp(
    campaign_id: str,
    request: Request,
    encounter_id: str | None = Query(None),
) -> Any:
    """Retrieve turn MVP awards and combatant performance statistics."""
    return await forward_json(
        request,
        method="GET",
        service="campaign_analytics",
        path=f"/api/v1/analytics/campaigns/{campaign_id}/mvp",
        params={"encounter_id": encounter_id} if encounter_id else None,
    )


@router.get(
    "/api/v1/analytics/campaigns/{campaign_id}/timeline",
    dependencies=[Depends(require_zanzibar_permission("view", "campaign", "campaign_id"))],
)
async def get_campaign_timeline(
    campaign_id: str,
    request: Request,
    session_id: str | None = Query(None),
) -> Any:
    """Retrieve chronological campaign milestones and narrative chronicle events."""
    return await forward_json(
        request,
        method="GET",
        service="campaign_analytics",
        path=f"/api/v1/analytics/campaigns/{campaign_id}/timeline",
        params={"session_id": session_id} if session_id else None,
    )
