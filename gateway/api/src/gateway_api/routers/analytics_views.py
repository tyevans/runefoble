"""Campaign Analytics proxy routes for heatmap, MVP, and timeline (TASK-0588).

Every route checks the `view` permission on the campaign in the Zanzibar schema. It then
forwards to the owning `campaign_analytics` service through the shared `ServiceClient`, with
the caller's bearer token and the query values the caller sent. The gateway never filters or
substitutes the owner's answer. Upstream failure returns 503 or 502 (ADR-0015 b).

The owner has no campaign summary route, so the gateway has none. A summary with literal
values would be a canned payload.
"""

from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from gateway_api.auth import require_zanzibar_permission
from gateway_api.proxy import forward_json

SERVICE = "campaign_analytics"
CAMPAIGNS = "/api/v1/analytics/campaigns"

router = APIRouter(tags=["Campaign Analytics Views"])


def _query(values: dict[str, str | None]) -> dict[str, str] | None:
    """Keep only the query values the caller sent. The owner validates each value."""
    present = {key: value for key, value in values.items() if value is not None}
    return present or None


@router.get(
    f"{CAMPAIGNS}/{{campaign_id}}/heatmap",
    dependencies=[Depends(require_zanzibar_permission("view", "campaign", "campaign_id"))],
)
async def get_campaign_heatmap(
    campaign_id: str,
    request: Request,
    session_id: str | None = Query(None),
    cell_size: str | None = Query(None),
    metric: str | None = Query(None),
) -> Any:
    """Retrieve spatial combat damage and strike heatmap data."""
    return await forward_json(
        request,
        method="GET",
        service=SERVICE,
        path=f"{CAMPAIGNS}/{campaign_id}/heatmap",
        params=_query({"session_id": session_id, "cell_size": cell_size, "metric": metric}),
    )


@router.get(
    f"{CAMPAIGNS}/{{campaign_id}}/mvp",
    dependencies=[Depends(require_zanzibar_permission("view", "campaign", "campaign_id"))],
)
async def get_campaign_mvp(
    campaign_id: str,
    request: Request,
    session_id: str | None = Query(None),
    encounter_id: str | None = Query(None),
) -> Any:
    """Retrieve turn MVP awards and combatant performance statistics."""
    return await forward_json(
        request,
        method="GET",
        service=SERVICE,
        path=f"{CAMPAIGNS}/{campaign_id}/mvp",
        params=_query({"session_id": session_id, "encounter_id": encounter_id}),
    )


@router.get(
    f"{CAMPAIGNS}/{{campaign_id}}/timeline",
    dependencies=[Depends(require_zanzibar_permission("view", "campaign", "campaign_id"))],
)
async def get_campaign_timeline(
    campaign_id: str,
    request: Request,
    session_id: str | None = Query(None),
    limit: str | None = Query(None),
) -> Any:
    """Retrieve chronological campaign milestones and narrative chronicle events."""
    return await forward_json(
        request,
        method="GET",
        service=SERVICE,
        path=f"{CAMPAIGNS}/{campaign_id}/timeline",
        params=_query({"session_id": session_id, "limit": limit}),
    )
