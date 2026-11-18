"""Campaign routes proxied to game_session, which owns campaign state (TASK-0590, TASK-0591).

The gateway verifies the bearer token, then forwards the request with that same token.
game_session checks every object permission (ADR-0007, ADR-0015). The gateway writes no
SpiceDB tuple here and keeps no campaign state. A failed upstream call returns the mapping
in `upstream_errors.py`: 503 when unreachable, 502 on upstream 5xx, upstream 4xx unchanged.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request, status
from gateway_api.auth import CurrentPrincipal
from gateway_api.character_store import character_store
from gateway_api.models import (
    AssignRoleRequest,
    CreateCampaignRequest,
    CreateCampaignSessionRequest,
    InviteRequest,
    JoinCampaignRequest,
    UpdateCampaignRequest,
)
from gateway_api.proxy import forward_json
from gateway_api.routers.tabletop import router as tabletop_router

SERVICE = "game_session"
CAMPAIGNS = "/api/v1/campaigns"

router = APIRouter(tags=["Campaigns & Sessions"])
router.include_router(tabletop_router)


@router.get("/api/v1/campaigns")
async def list_campaigns(request: Request, user: CurrentPrincipal) -> Any:
    """List the campaigns the caller can view (game_session)."""
    return await forward_json(request, service=SERVICE, method="GET", path=CAMPAIGNS)


@router.post("/api/v1/campaigns", status_code=status.HTTP_201_CREATED)
async def create_campaign(
    req: CreateCampaignRequest, request: Request, user: CurrentPrincipal
) -> Any:
    """Create a campaign. The caller becomes its owner (game_session)."""
    return await forward_json(
        request,
        service=SERVICE,
        method="POST",
        path=CAMPAIGNS,
        json_body=req.model_dump(mode="json"),
    )


@router.get("/api/v1/campaigns/{campaign_id}")
async def get_campaign(campaign_id: str, request: Request, user: CurrentPrincipal) -> Any:
    """Read one campaign. Requires `view` (game_session)."""
    return await forward_json(
        request, service=SERVICE, method="GET", path=f"{CAMPAIGNS}/{campaign_id}"
    )


@router.patch("/api/v1/campaigns/{campaign_id}")
async def update_campaign(
    campaign_id: str,
    req: UpdateCampaignRequest,
    request: Request,
    user: CurrentPrincipal,
) -> Any:
    """Update campaign fields. Requires `manage` (game_session)."""
    return await forward_json(
        request,
        service=SERVICE,
        method="PATCH",
        path=f"{CAMPAIGNS}/{campaign_id}",
        json_body=req.model_dump(mode="json", exclude_unset=True),
    )


@router.get("/api/v1/campaigns/{campaign_id}/capabilities")
async def get_campaign_capabilities(
    campaign_id: str, request: Request, user: CurrentPrincipal
) -> Any:
    """Report which campaign actions the caller holds (game_session)."""
    return await forward_json(
        request, service=SERVICE, method="GET", path=f"{CAMPAIGNS}/{campaign_id}/capabilities"
    )


@router.post("/api/v1/campaigns/{campaign_id}/invites", status_code=status.HTTP_201_CREATED)
async def create_campaign_invite(
    campaign_id: str, req: InviteRequest, request: Request, user: CurrentPrincipal
) -> Any:
    """Issue a shareable invite. Requires `run_session` (game_session)."""
    return await forward_json(
        request,
        service=SERVICE,
        method="POST",
        path=f"{CAMPAIGNS}/{campaign_id}/invites",
        json_body=req.model_dump(mode="json"),
    )


@router.post("/api/v1/campaigns/join")
async def join_campaign(req: JoinCampaignRequest, request: Request, user: CurrentPrincipal) -> Any:
    """Redeem an invite token and join the campaign (game_session)."""
    return await forward_json(
        request,
        service=SERVICE,
        method="POST",
        path=f"{CAMPAIGNS}/join",
        json_body=req.model_dump(mode="json"),
    )


@router.get("/api/v1/campaigns/{campaign_id}/members")
async def list_campaign_members(campaign_id: str, request: Request, user: CurrentPrincipal) -> Any:
    """List the owner and every member. Requires `view` (game_session).

    The gateway adds each member's character name from its own character store.
    """
    members = await forward_json(
        request, service=SERVICE, method="GET", path=f"{CAMPAIGNS}/{campaign_id}/members"
    )
    names = _character_names(campaign_id)
    for member in members:
        member["character_name"] = member.get("character_name") or names.get(member["user_id"])
    return members


def _character_names(campaign_id: str) -> dict[str, str]:
    """Return {owner id: character name} for the characters assigned to one campaign."""
    names: dict[str, str] = {}
    for char in character_store.list_characters():
        if char.campaign_id == campaign_id:
            names.setdefault(char.owner_id, char.name)
    return names


@router.delete("/api/v1/campaigns/{campaign_id}/members/{user_id}")
async def remove_campaign_member(
    campaign_id: str, user_id: str, request: Request, user: CurrentPrincipal
) -> Any:
    """Remove a member and revoke their campaign relations. Requires `manage` (game_session)."""
    return await forward_json(
        request,
        service=SERVICE,
        method="DELETE",
        path=f"{CAMPAIGNS}/{campaign_id}/members/{user_id}",
    )


@router.post("/api/v1/campaigns/{campaign_id}/roles")
async def assign_campaign_role(
    campaign_id: str, req: AssignRoleRequest, request: Request, user: CurrentPrincipal
) -> Any:
    """Grant a campaign role. Requires `manage` (game_session)."""
    return await forward_json(
        request,
        service=SERVICE,
        method="POST",
        path=f"{CAMPAIGNS}/{campaign_id}/roles",
        json_body=req.model_dump(mode="json"),
    )


@router.get("/api/v1/campaigns/{campaign_id}/sessions")
async def list_campaign_sessions(campaign_id: str, request: Request, user: CurrentPrincipal) -> Any:
    """List the sessions and lobbies of a campaign. Requires `view` (game_session)."""
    return await forward_json(
        request, service=SERVICE, method="GET", path=f"{CAMPAIGNS}/{campaign_id}/sessions"
    )


@router.post("/api/v1/campaigns/{campaign_id}/sessions", status_code=status.HTTP_201_CREATED)
async def create_campaign_session(
    campaign_id: str,
    req: CreateCampaignSessionRequest,
    request: Request,
    user: CurrentPrincipal,
) -> Any:
    """Create a session or staging lobby. Requires `run_session` (game_session)."""
    return await forward_json(
        request,
        service=SERVICE,
        method="POST",
        path=f"{CAMPAIGNS}/{campaign_id}/sessions",
        json_body=req.model_dump(mode="json"),
    )
