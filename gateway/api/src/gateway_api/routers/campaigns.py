"""Campaign, session, board, and role management router for Runefoble Gateway API."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from gateway_api.auth import get_current_user, get_spicedb_client, require_zanzibar_permission
from gateway_api.campaign_store import (
    DEFAULT_BOARD_TOKENS,
    DEFAULT_SESSION_PARTICIPANTS,
    build_campaign_summary,
    campaign_store,
    format_invite_response,
    get_all_viewable_campaigns,
    get_campaign_members,
    join_from_invite,
)
from gateway_api.dependencies import ws_manager
from gateway_api.models import (
    AdvanceTurnRequest,
    AssignRoleRequest,
    AtmosphereUpdateRequest,
    CampaignMemberResponse,
    CampaignSummaryResponse,
    CreateCampaignRequest,
    DMOverrideRequest,
    InviteRequest,
    InviteResponse,
    JoinCampaignRequest,
    JoinCampaignResponse,
    TokenMoveRequest,
    UpdateCampaignRequest,
)
from runefoble_auth.zitadel import AuthenticatedUser

router = APIRouter(tags=["Campaigns & Sessions"])


@router.get("/api/v1/profile")
async def get_profile(user: Annotated[AuthenticatedUser, Depends(get_current_user)]) -> dict:
    """Retrieve authenticated Zitadel user profile claims."""
    return {
        "user_id": user.user_id,
        "username": user.username,
        "email": user.email,
        "roles": user.roles,
        "is_admin": user.is_admin,
    }


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
    await get_spicedb_client().write_relationship("campaign", cid, "owner", "user", user.user_id)
    return camp.to_summary(role="owner", member_count=1)


@router.get(
    "/api/v1/campaigns/{campaign_id}",
    dependencies=[Depends(require_zanzibar_permission("view", "campaign", "campaign_id"))],
)
async def get_campaign_proxy(campaign_id: str) -> dict:
    """Retrieve campaign overview details (requires 'view')."""
    camp = campaign_store.get_campaign(campaign_id)
    return (
        camp.to_dict()
        if camp
        else {
            "id": campaign_id,
            "campaign_id": campaign_id,
            "title": f"Campaign {campaign_id}",
            "status": "active",
        }
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
    "/api/v1/sessions/{session_id}",
    dependencies=[Depends(require_zanzibar_permission("view", resource_type="campaign"))],
)
async def get_session_proxy(session_id: str) -> dict:
    """Retrieve game session state, participants, and round index (requires 'view')."""
    return {
        "id": session_id,
        "campaign_id": session_id,
        "status": "active",
        "round": 3,
        "current_turn": "c1",
        "participants": DEFAULT_SESSION_PARTICIPANTS,
    }


@router.post(
    "/api/v1/sessions/{session_id}/turns/advance",
    dependencies=[Depends(require_zanzibar_permission("run_session", resource_type="campaign"))],
)
async def advance_turn_proxy(session_id: str, req: AdvanceTurnRequest) -> dict:
    return {
        "session_id": session_id,
        "status": "turn_advanced",
        "active_character_id": req.next_character_id,
    }


@router.post(
    "/api/v1/sessions/{session_id}/dm-override",
    dependencies=[Depends(require_zanzibar_permission("run_session", resource_type="campaign"))],
)
async def dm_override_proxy(session_id: str, req: DMOverrideRequest) -> dict:
    return {
        "session_id": session_id,
        "status": "override_executed",
        "action": req.action,
        "reason": req.reason,
    }


@router.post(
    "/api/v1/sessions/{session_id}/atmosphere",
    dependencies=[Depends(require_zanzibar_permission("run_session", resource_type="campaign"))],
)
async def update_atmosphere_proxy(session_id: str, req: AtmosphereUpdateRequest) -> dict:
    return {
        "session_id": session_id,
        "status": "atmosphere_updated",
        "atmosphere": req.model_dump(),
    }


@router.post(
    "/api/v1/board/tokens/{token_id}/move",
    dependencies=[Depends(require_zanzibar_permission("move", "board_token", "token_id"))],
)
async def move_token_proxy(token_id: str, req: TokenMoveRequest) -> dict:
    return {"token_id": token_id, "status": "token_moved", "to_x": req.to_x, "to_y": req.to_y}


@router.get(
    "/api/v1/board/tokens/{token_id}",
    dependencies=[Depends(require_zanzibar_permission("inspect", "board_token", "token_id"))],
)
async def get_token_proxy(token_id: str) -> dict:
    return {"token_id": token_id, "status": "active", "x": 2, "y": 3}


@router.get(
    "/api/v1/boards/{session_id}",
    dependencies=[Depends(require_zanzibar_permission("view", resource_type="campaign"))],
)
async def get_board_proxy(session_id: str) -> dict:
    return {"session_id": session_id, "cols": 8, "rows": 8, "tokens": DEFAULT_BOARD_TOKENS}


@router.post("/api/v1/watcher/speak-and-act")
async def speak_and_act(transcript: str, speaker_name: str, session_id: str) -> dict:
    event = {
        "type": "speech_action",
        "speaker": speaker_name,
        "transcript": transcript,
        "action_taken": "Valeros stepped forward 2 squares.",
        "watcher_commentary": "The Watcher observes your advance into the crypt.",
    }
    await ws_manager.broadcast(event)
    return event
