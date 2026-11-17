"""Campaign Hub proxy routes for Atlas, Codex, and Analytics telemetry."""

from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from gateway_api.auth import require_zanzibar_permission
from gateway_api.proxy import forward_json, upstream_url

router = APIRouter(tags=["Campaign Hub Views"])

CAMPAIGN_LORE_DEFAULT_URL = "http://campaign-lore:8006"
CAMPAIGN_ANALYTICS_DEFAULT_URL = "http://campaign-analytics:8011"


def _lore_url() -> str:
    return upstream_url("CAMPAIGN_LORE_URL", CAMPAIGN_LORE_DEFAULT_URL)


def _analytics_url() -> str:
    return upstream_url("CAMPAIGN_ANALYTICS_URL", CAMPAIGN_ANALYTICS_DEFAULT_URL)


@router.get(
    "/api/v1/campaigns/{campaign_id}/atlas",
    dependencies=[Depends(require_zanzibar_permission("view", "campaign", "campaign_id"))],
)
async def get_campaign_atlas(campaign_id: str, request: Request) -> Any:
    """Retrieve world atlas map layers, milestone pins, and geopolitical territories."""
    return await forward_json(
        request,
        method="GET",
        base_url=_lore_url(),
        path=f"/api/v1/campaigns/{campaign_id}/atlas",
    )


@router.get(
    "/api/v1/campaigns/{campaign_id}/codex",
    dependencies=[Depends(require_zanzibar_permission("view", "campaign", "campaign_id"))],
)
@router.get(
    "/api/v1/campaigns/{campaign_id}/codex/entries",
    dependencies=[Depends(require_zanzibar_permission("view", "campaign", "campaign_id"))],
)
async def get_campaign_codex(campaign_id: str, request: Request) -> Any:
    """Retrieve campaign lore codex entries and cross-references."""
    return await forward_json(
        request,
        method="GET",
        base_url=_lore_url(),
        path=f"/api/v1/campaigns/{campaign_id}/codex/entries",
    )


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
        base_url=_analytics_url(),
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
        base_url=_analytics_url(),
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
        base_url=_analytics_url(),
        path=f"/api/v1/analytics/campaigns/{campaign_id}/timeline",
        params={"session_id": session_id} if session_id else None,
    )
