"""Campaign routes proxied to game_session, which owns campaign state (TASK-0590, TASK-0591).

The gateway verifies the bearer token, then forwards the request with that same token.
game_session checks every object permission (ADR-0007, ADR-0015). The gateway writes no
SpiceDB tuple here and keeps no campaign state. A failed upstream call returns the mapping
in `upstream_errors.py`: 503 when unreachable, 502 on upstream 5xx, upstream 4xx unchanged.

Pass-through routes are rows in `ROUTES` (TASK-0822). Two routes stay hand-written: the PATCH
sends only the fields the caller set, and the member list adds each character name.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request, status
from gateway_api.auth import CallerPrincipal
from gateway_api.character_view import campaign_character_names
from gateway_api.models import (
    AssignRoleRequest,
    CreateCampaignRequest,
    CreateCampaignSessionRequest,
    InviteRequest,
    JoinCampaignRequest,
    UpdateCampaignRequest,
)
from gateway_api.proxy import forward_json
from gateway_api.proxy_table import ProxyRoute, register_proxy_routes
from runefoble_platform.service_client import owner_routes

SERVICE = "game_session"
CAMPAIGNS = "/api/v1/campaigns"

router = APIRouter(tags=["Campaigns & Sessions"])

ROUTES = (
    ProxyRoute(
        "GET",
        "/api/v1/campaigns",
        ("api", "v1", "campaigns"),
        SERVICE,
        name="list_campaigns",
        doc="List the campaigns the caller can view (game_session).",
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/campaigns",
        ("api", "v1", "campaigns"),
        SERVICE,
        name="create_campaign",
        doc="Create a campaign. The caller becomes its owner (game_session).",
        body="json",
        body_model=CreateCampaignRequest,
        principal=True,
        status_code=status.HTTP_201_CREATED,
    ),
    ProxyRoute(
        "GET",
        "/api/v1/campaigns/{campaign_id}",
        (),
        SERVICE,
        name="get_campaign",
        doc="Read one campaign. Requires `view` (game_session).",
        owner=owner_routes.get_campaign,
        principal=True,
    ),
    ProxyRoute(
        "GET",
        "/api/v1/campaigns/{campaign_id}/capabilities",
        ("api", "v1", "campaigns", "{campaign_id}", "capabilities"),
        SERVICE,
        name="get_campaign_capabilities",
        doc="Report which campaign actions the caller holds (game_session).",
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/campaigns/{campaign_id}/invites",
        ("api", "v1", "campaigns", "{campaign_id}", "invites"),
        SERVICE,
        name="create_campaign_invite",
        doc="Issue a shareable invite. Requires `run_session` (game_session).",
        body="json",
        body_model=InviteRequest,
        principal=True,
        status_code=status.HTTP_201_CREATED,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/campaigns/join",
        ("api", "v1", "campaigns", "join"),
        SERVICE,
        name="join_campaign",
        doc="Redeem an invite token and join the campaign (game_session).",
        body="json",
        body_model=JoinCampaignRequest,
        principal=True,
    ),
    ProxyRoute(
        "DELETE",
        "/api/v1/campaigns/{campaign_id}/members/{user_id}",
        ("api", "v1", "campaigns", "{campaign_id}", "members", "{user_id}"),
        SERVICE,
        name="remove_campaign_member",
        doc=(
            "Remove a member and revoke their campaign relations. Requires `manage` (game_session)."
        ),
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/campaigns/{campaign_id}/roles",
        ("api", "v1", "campaigns", "{campaign_id}", "roles"),
        SERVICE,
        name="assign_campaign_role",
        doc="Grant a campaign role. Requires `manage` (game_session).",
        body="json",
        body_model=AssignRoleRequest,
        principal=True,
    ),
    ProxyRoute(
        "GET",
        "/api/v1/campaigns/{campaign_id}/sessions",
        ("api", "v1", "campaigns", "{campaign_id}", "sessions"),
        SERVICE,
        name="list_campaign_sessions",
        doc="List the sessions and lobbies of a campaign. Requires `view` (game_session).",
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/campaigns/{campaign_id}/sessions/reconcile-links",
        ("api", "v1", "campaigns", "{campaign_id}", "sessions", "reconcile-links"),
        SERVICE,
        name="reconcile_campaign_session_links",
        doc="Rewrite the campaign link of every session. Requires `run_session` (game_session).",
        principal=True,
    ),
    ProxyRoute(
        "POST",
        "/api/v1/campaigns/{campaign_id}/sessions",
        ("api", "v1", "campaigns", "{campaign_id}", "sessions"),
        SERVICE,
        name="create_campaign_session",
        doc="Create a session or staging lobby. Requires `run_session` (game_session).",
        body="json",
        body_model=CreateCampaignSessionRequest,
        principal=True,
        status_code=status.HTTP_201_CREATED,
    ),
)


@router.patch("/api/v1/campaigns/{campaign_id}")
async def update_campaign(
    campaign_id: str,
    req: UpdateCampaignRequest,
    request: Request,
    user: CallerPrincipal,
) -> Any:
    """Update campaign fields. Requires `manage` (game_session)."""
    return await forward_json(
        request,
        service=SERVICE,
        method="PATCH",
        path=f"{CAMPAIGNS}/{campaign_id}",
        json_body=req.model_dump(mode="json", exclude_unset=True),
    )


@router.get("/api/v1/campaigns/{campaign_id}/members")
async def list_campaign_members(campaign_id: str, request: Request, user: CallerPrincipal) -> Any:
    """List the owner and every member. Requires `view` (game_session).

    The gateway adds each member's character name from its own character store.
    """
    members = await forward_json(
        request, service=SERVICE, method="GET", path=f"{CAMPAIGNS}/{campaign_id}/members"
    )
    names = await campaign_character_names(request, campaign_id)
    for member in members:
        member["character_name"] = member.get("character_name") or names.get(member["user_id"])
    return members


register_proxy_routes(router, ROUTES)
