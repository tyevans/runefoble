"""Campaign Lore proxy routes for the Atlas and the Codex (TASK-0587, TASK-0695).

Every route forwards to the owning `campaign_lore` service through the shared `ServiceClient`.
The gateway verifies the caller's bearer token, then forwards it. The owner checks the object
permission in the Zanzibar schema. It never filters or substitutes the owner's answer. Upstream
failure returns 503 or 502, never canned data (ADR-0015).

The one gateway check is the atlas pin route. It requires `run_session`, and the owner checks
`play` on that route, which is a different permission. The gateway check keeps the stricter rule
until the owner checks `run_session` too (TASK-0845).
"""

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Query, Request
from gateway_api.auth import get_principal, require_zanzibar_permission
from gateway_api.proxy import forward_json

SERVICE = "campaign_lore"
CAMPAIGNS = "/api/v1/campaigns"

router = APIRouter(tags=["Campaign Lore Views"])

_VERIFIED = [Depends(get_principal)]


def _query(values: dict[str, str | None]) -> dict[str, str] | None:
    """Keep only the query values the caller sent."""
    present = {key: value for key, value in values.items() if value is not None}
    return present or None


@router.get(
    "/api/v1/campaigns/{campaign_id}/atlas",
    dependencies=_VERIFIED,
)
async def get_campaign_atlas(
    campaign_id: str,
    request: Request,
    layer: str | None = Query(None),
    era: str | None = Query(None),
    session_id: str | None = Query(None),
) -> Any:
    """Retrieve world atlas map layers, milestone pins, and geopolitical territories."""
    return await forward_json(
        request,
        method="GET",
        service=SERVICE,
        path=f"{CAMPAIGNS}/{campaign_id}/atlas",
        params=_query({"layer": layer, "era": era, "session_id": session_id}),
    )


@router.post(
    "/api/v1/campaigns/{campaign_id}/atlas/pins",
    status_code=201,
    dependencies=[Depends(require_zanzibar_permission("run_session", "campaign", "campaign_id"))],
)
async def create_campaign_atlas_pin(
    campaign_id: str,
    request: Request,
    body: Annotated[dict[str, Any], Body()],
) -> Any:
    """Place a milestone pin on the atlas. Requires `run_session`, the permission to mutate the world."""
    return await forward_json(
        request,
        method="POST",
        service=SERVICE,
        path=f"{CAMPAIGNS}/{campaign_id}/atlas/pins",
        json_body=body,
    )


@router.get("/api/v1/campaigns/{campaign_id}/codex", dependencies=_VERIFIED)
async def get_campaign_codex(
    campaign_id: str,
    request: Request,
    era: str | None = Query(None),
    tag: str | None = Query(None),
    search: str | None = Query(None),
) -> Any:
    """Retrieve campaign lore codex entries. The owner applies the privacy checks."""
    return await forward_json(
        request,
        method="GET",
        service=SERVICE,
        path=f"{CAMPAIGNS}/{campaign_id}/codex/entries",
        params=_query({"era": era, "tag": tag, "search": search}),
    )


@router.post(
    "/api/v1/campaigns/{campaign_id}/codex/entries",
    status_code=201,
    dependencies=_VERIFIED,
)
async def publish_campaign_codex_entry(
    campaign_id: str,
    request: Request,
    body: Annotated[dict[str, Any], Body()],
) -> Any:
    """Publish a journal or secret codex entry. Requires `play`, the permission for player assets."""
    return await forward_json(
        request,
        method="POST",
        service=SERVICE,
        path=f"{CAMPAIGNS}/{campaign_id}/codex/entries",
        json_body=body,
    )
