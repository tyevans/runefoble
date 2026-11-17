import contextlib
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from gateway_api.auth import CurrentPrincipal, get_spicedb_client, require_zanzibar_permission
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
from gateway_api.routers.tabletop import router as tabletop_router
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Campaigns & Sessions"])
router.include_router(tabletop_router)


@router.get("/api/v1/campaigns", response_model=list[CampaignSummaryResponse])
async def list_campaigns(
    user: CurrentPrincipal,
) -> list[CampaignSummaryResponse]:
    """List all campaigns the authenticated user has Zanzibar permission to view."""
    return await get_all_viewable_campaigns(user.user_id, get_spicedb_client())


@router.post(
    "/api/v1/campaigns", response_model=CampaignSummaryResponse, status_code=status.HTTP_201_CREATED
)
async def create_campaign(
    req: CreateCampaignRequest, user: CurrentPrincipal
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
    user: CurrentPrincipal,
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
    user: CurrentPrincipal,
) -> InviteResponse:
    """Generate shareable invite token for a campaign (requires 'run_session' / DM/owner)."""
    inv = campaign_store.create_invite(
        campaign_id, req.role, user.user_id, req.expires_in_hours, req.max_uses
    )
    return format_invite_response(inv)


@router.post("/api/v1/campaigns/join", response_model=JoinCampaignResponse)
async def join_campaign(req: JoinCampaignRequest, user: CurrentPrincipal) -> JoinCampaignResponse:
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


@router.delete(
    "/api/v1/campaigns/{campaign_id}/members/{user_id}",
    dependencies=[Depends(require_zanzibar_permission("manage", "campaign", "campaign_id"))],
)
async def remove_campaign_member(
    campaign_id: str,
    user_id: str,
    user: CurrentPrincipal,
) -> dict:
    """Remove a member from a campaign by deleting their SpiceDB Zanzibar relationships."""
    spicedb = get_spicedb_client()
    rels = await spicedb.read_relationships(resource_type="campaign", resource_id=campaign_id)
    removed_any = False
    for r in rels:
        if r.subject_id == user_id:
            await spicedb.delete_relationship(
                "campaign", campaign_id, r.relation, r.subject_type, user_id
            )
            removed_any = True

    if not removed_any:
        for rel in ("player", "spectator", "dungeon_master", "owner"):
            with contextlib.suppress(Exception):
                await spicedb.delete_relationship("campaign", campaign_id, rel, "user", user_id)

    camp = campaign_store.get_campaign(campaign_id)
    if camp and camp.owner_id == user_id:
        camp.owner_id = ""

    return {
        "status": "member_removed",
        "campaign_id": campaign_id,
        "user_id": user_id,
    }


@router.post(
    "/api/v1/campaigns/{campaign_id}/roles",
    dependencies=[Depends(require_zanzibar_permission("manage", "campaign", "campaign_id"))],
)
async def assign_campaign_role(
    campaign_id: str,
    req: AssignRoleRequest,
    user: CurrentPrincipal,
) -> dict:
    """Grant a campaign role as a SpiceDB Zanzibar tuple (requires 'manage'; owner only)."""
    try:
        await get_spicedb_client().write_relationship(
            "campaign", campaign_id, req.role, "user", req.user_id
        )
    except Exception as exc:
        logger.exception("Role grant failed for campaign %s", campaign_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authorization store is unavailable. The role was not granted.",
        ) from exc
    return {
        "status": "role_assigned",
        "campaign_id": campaign_id,
        "user_id": req.user_id,
        "role": req.role,
        "zanzibar_relation": f"campaign:{campaign_id}#{req.role}@user:{req.user_id}",
    }


class CampaignCapabilitiesResponse(BaseModel):
    """Per-campaign capability flags for the caller, each from a SpiceDB permission check."""

    manage: bool
    run_session: bool
    play: bool
    view: bool


@router.get(
    "/api/v1/campaigns/{campaign_id}/capabilities",
    response_model=CampaignCapabilitiesResponse,
)
async def get_campaign_capabilities(
    campaign_id: str,
    user: CurrentPrincipal,
) -> CampaignCapabilitiesResponse:
    """Report which campaign actions the caller holds. Non-members receive all false."""
    spicedb = get_spicedb_client()

    async def _has(permission: str) -> bool:
        return await spicedb.check_permission(
            "campaign", campaign_id, permission, "user", user.user_id
        )

    return CampaignCapabilitiesResponse(
        manage=await _has("manage"),
        run_session=await _has("run_session"),
        play=await _has("play"),
        view=await _has("view"),
    )


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
    user: CurrentPrincipal,
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
