"""Campaign, session lifecycle, and role management router for Runefoble Gateway API."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from gateway_api.auth import get_current_user, get_spicedb_client, require_zanzibar_permission
from gateway_api.campaign_store import (
    build_campaign_summary,
    campaign_store,
    format_invite_response,
    get_all_viewable_campaigns,
    get_campaign_members,
    join_from_invite,
)
from gateway_api.models import (
    AssignRoleRequest,
    CampaignMemberResponse,
    CampaignSessionResponse,
    CampaignSummaryResponse,
    CreateCampaignRequest,
    CreateCampaignSessionRequest,
    InviteRequest,
    InviteResponse,
    JoinCampaignRequest,
    JoinCampaignResponse,
    UpdateCampaignRequest,
)
from gateway_api.routers.auth.profile import router as profile_router
from gateway_api.routers.tabletop import router as tabletop_router
from runefoble_auth.zitadel import AuthenticatedUser

router = APIRouter(tags=["Campaigns & Sessions"])
router.include_router(tabletop_router)
router.include_router(profile_router)


@router.get("/api/v1/campaigns", response_model=list[CampaignSummaryResponse])
async def list_campaigns(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> list[CampaignSummaryResponse]:
    """List all campaigns the authenticated user has Zanzibar permission to view."""
    return await get_all_viewable_campaigns(user.user_id, get_spicedb_client())


@router.post(
    "/api/v1/campaigns", response_model=CampaignSummaryResponse, status_code=status.HTTP_201_CREATED
)
async def create_campaign(
    req: CreateCampaignRequest, user: Annotated[AuthenticatedUser, Depends(get_current_user)]
) -> CampaignSummaryResponse:
    """Create a new campaign and write owner relation to SpiceDB Zanzibar."""
    cid, camp = campaign_store.create_from_request(req, user.user_id)
    spicedb = get_spicedb_client()
    await spicedb.write_relationship("campaign", cid, "owner", "user", user.user_id)
    for sess in campaign_store.get_campaign_sessions(cid):
        await spicedb.write_relationship("session", sess.id, "campaign", "campaign", cid)
        await spicedb.write_relationship("game_session", sess.id, "campaign", "campaign", cid)
    return camp.to_summary(role="owner", member_count=1)


@router.get(
    "/api/v1/campaigns/{campaign_id}",
    dependencies=[Depends(require_zanzibar_permission("view", "campaign", "campaign_id"))],
)
async def get_campaign_proxy(campaign_id: str) -> dict:
    camp = campaign_store.get_campaign(campaign_id)
    return (
        camp.to_dict()
        if camp
        else {"id": campaign_id, "title": f"Campaign {campaign_id}", "status": "active"}
    )


@router.patch(
    "/api/v1/campaigns/{campaign_id}",
    response_model=CampaignSummaryResponse,
    dependencies=[Depends(require_zanzibar_permission("manage", "campaign", "campaign_id"))],
)
async def update_campaign(
    campaign_id: str,
    req: UpdateCampaignRequest,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> CampaignSummaryResponse:
    """Update campaign title, description, and settings (requires 'manage' permission)."""
    camp = campaign_store.update_from_request(campaign_id, req, user.user_id)
    return await build_campaign_summary(camp, user.user_id, get_spicedb_client())


@router.post(
    "/api/v1/campaigns/{campaign_id}/invites",
    response_model=InviteResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_zanzibar_permission("run_session", "campaign", "campaign_id"))],
)
async def create_campaign_invite(
    campaign_id: str,
    req: InviteRequest,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> InviteResponse:
    """Generate shareable invite token for a campaign (requires 'run_session' / DM/owner)."""
    inv = campaign_store.create_invite(
        campaign_id, req.role, user.user_id, req.expires_in_hours, req.max_uses
    )
    return format_invite_response(inv)


@router.post("/api/v1/campaigns/join", response_model=JoinCampaignResponse)
async def join_campaign(
    req: JoinCampaignRequest, user: Annotated[AuthenticatedUser, Depends(get_current_user)]
) -> JoinCampaignResponse:
    """Accept an invite token and register membership in SpiceDB Zanzibar."""
    return await join_from_invite(req.invite_token, user.user_id, get_spicedb_client())


@router.get(
    "/api/v1/campaigns/{campaign_id}/members",
    response_model=list[CampaignMemberResponse],
    dependencies=[Depends(require_zanzibar_permission("view", "campaign", "campaign_id"))],
)
async def list_campaign_members(campaign_id: str) -> list[CampaignMemberResponse]:
    """List all members and their active Zanzibar roles (requires 'view')."""
    return await get_campaign_members(campaign_id, get_spicedb_client())


@router.post("/api/v1/campaigns/{campaign_id}/roles")
async def assign_campaign_role(campaign_id: str, req: AssignRoleRequest) -> dict:
    """Write fine-grained relationship tuple to SpiceDB Zanzibar."""
    rel = "spectator" if req.role == "spectator" else req.role
    await get_spicedb_client().write_relationship("campaign", campaign_id, rel, "user", req.user_id)
    return {
        "status": "role_assigned",
        "campaign_id": campaign_id,
        "user_id": req.user_id,
        "role": req.role,
        "zanzibar_relation": f"campaign:{campaign_id}#{rel}@user:{req.user_id}",
    }


@router.get(
    "/api/v1/campaigns/{campaign_id}/sessions",
    response_model=list[CampaignSessionResponse],
    dependencies=[Depends(require_zanzibar_permission("view", "campaign", "campaign_id"))],
)
async def list_campaign_sessions(campaign_id: str) -> list[CampaignSessionResponse]:
    """List all sessions belonging to a campaign (requires Zanzibar 'view' permission)."""
    sessions = campaign_store.get_campaign_sessions(campaign_id)
    return [s.to_response() for s in sessions]


@router.post(
    "/api/v1/campaigns/{campaign_id}/sessions",
    response_model=CampaignSessionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_zanzibar_permission("run_session", "campaign", "campaign_id"))],
)
async def create_campaign_session(
    campaign_id: str,
    req: CreateCampaignSessionRequest,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> CampaignSessionResponse:
    """Create a new session or staging lobby for a campaign (requires 'run_session' permission)."""
    session_rec = campaign_store.create_session(
        campaign_id=campaign_id,
        title=req.title,
        status=req.status,
        scheduled_at=req.scheduled_at,
        description=req.description,
    )
    spicedb = get_spicedb_client()
    await spicedb.write_relationship("session", session_rec.id, "campaign", "campaign", campaign_id)
    await spicedb.write_relationship(
        "game_session", session_rec.id, "campaign", "campaign", campaign_id
    )
    return session_rec.to_response()
