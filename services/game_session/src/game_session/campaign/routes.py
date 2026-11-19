"""Campaign lifecycle routes under /api/v1/campaigns. Owned by game_session (ADR-0015 a).

Every route verifies the Zitadel bearer token itself (ADR-0015 c). Every object-level
check uses SpiceDB permissions (Hard Invariant 1).
"""

from __future__ import annotations

from typing import Annotated

from eventsource.application.aggregates.repository import AggregateRepository
from fastapi import APIRouter, Depends, status
from game_session.aggregate import GameSessionAggregate
from game_session.campaign import service_campaigns as campaigns
from game_session.campaign import service_membership as membership
from game_session.campaign import service_roles as roles
from game_session.campaign.permissions import (
    ManageCampaign,
    RunSessionCampaign,
    ViewCampaign,
)
from game_session.campaign.repositories import CampaignRepositories, get_campaign_repositories
from game_session.campaign.schemas import (
    AssignRoleRequest,
    CampaignCapabilitiesResponse,
    CampaignMemberResponse,
    CampaignSessionResponse,
    CampaignSummaryResponse,
    CreateCampaignRequest,
    CreateCampaignSessionRequest,
    InviteRequest,
    InviteResponse,
    JoinCampaignRequest,
    JoinCampaignResponse,
    MemberRemovedResponse,
    RoleAssignedResponse,
    SessionLinkReconcileResponse,
    UpdateCampaignRequest,
)
from game_session.campaign.tuples import SpiceDB
from game_session.dependencies import get_game_session_repository
from game_session.profile.aggregate import UserProfileAggregate
from game_session.profile.repository import get_profile_repository
from game_session.settlement.auth.tokens import CallerPrincipal, get_principal
from runefoble_auth.factory import get_spicedb_client

router = APIRouter(
    dependencies=[Depends(get_principal)],
    prefix="/api/v1/campaigns",
    tags=["Campaigns & Sessions"],
)

Repos = Annotated[CampaignRepositories, Depends(get_campaign_repositories)]
Spicedb = Annotated[SpiceDB, Depends(get_spicedb_client)]
GameSessions = Annotated[
    AggregateRepository[GameSessionAggregate], Depends(get_game_session_repository)
]
ProfileRepo = Annotated[AggregateRepository[UserProfileAggregate], Depends(get_profile_repository)]


@router.get("", response_model=list[CampaignSummaryResponse])
async def list_campaigns(
    principal: CallerPrincipal, repos: Repos, spicedb: Spicedb
) -> list[CampaignSummaryResponse]:
    """List the campaigns the caller can view."""
    return await campaigns.list_viewable_campaigns(repos, spicedb, principal.user_id)


@router.post("", response_model=CampaignSummaryResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    req: CreateCampaignRequest,
    principal: CallerPrincipal,
    repos: Repos,
    spicedb: Spicedb,
    game_sessions: GameSessions,
) -> CampaignSummaryResponse:
    """Create a campaign. The caller becomes its owner."""
    return await campaigns.create_campaign(
        repos, spicedb, principal.user_id, principal.username, req, game_sessions
    )


@router.get("/{campaign_id}", response_model=CampaignSummaryResponse)
async def get_campaign(
    campaign_id: str,
    principal: ViewCampaign,
    repos: Repos,
    spicedb: Spicedb,
) -> CampaignSummaryResponse:
    """Read one campaign. Requires `view`."""
    return await campaigns.get_campaign(repos, spicedb, campaign_id, principal.user_id)


@router.patch("/{campaign_id}", response_model=CampaignSummaryResponse)
async def update_campaign(
    campaign_id: str,
    req: UpdateCampaignRequest,
    principal: ManageCampaign,
    repos: Repos,
    spicedb: Spicedb,
) -> CampaignSummaryResponse:
    """Update campaign fields. Requires `manage`."""
    return await campaigns.update_campaign(repos, spicedb, campaign_id, req, principal.user_id)


@router.post(
    "/{campaign_id}/invites",
    response_model=InviteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_invite(
    campaign_id: str,
    req: InviteRequest,
    principal: RunSessionCampaign,
    repos: Repos,
) -> InviteResponse:
    """Issue a shareable invite. Requires `run_session`."""
    return await membership.create_invite(repos, campaign_id, req, principal.user_id)


@router.post("/join", response_model=JoinCampaignResponse)
async def join_campaign(
    req: JoinCampaignRequest,
    principal: CallerPrincipal,
    repos: Repos,
    spicedb: Spicedb,
) -> JoinCampaignResponse:
    """Redeem an invite and join the campaign with the invite's role."""
    return await membership.join_campaign(
        repos, spicedb, req.invite_token, principal.user_id, principal.username
    )


@router.get("/{campaign_id}/members", response_model=list[CampaignMemberResponse])
async def list_members(
    campaign_id: str,
    principal: ViewCampaign,
    repos: Repos,
    profiles: ProfileRepo,
) -> list[CampaignMemberResponse]:
    """List the owner and every member with their names. Requires `view`."""
    return await membership.list_members(repos, profiles, campaign_id)


@router.delete("/{campaign_id}/members/{user_id}", response_model=MemberRemovedResponse)
async def remove_member(
    campaign_id: str,
    user_id: str,
    principal: ManageCampaign,
    repos: Repos,
    spicedb: Spicedb,
) -> MemberRemovedResponse:
    """Remove a member and revoke their campaign relations. Requires `manage`."""
    return await membership.remove_member(repos, spicedb, campaign_id, user_id)


@router.get("/{campaign_id}/sessions", response_model=list[CampaignSessionResponse])
async def list_sessions(
    campaign_id: str,
    principal: ViewCampaign,
    repos: Repos,
) -> list[CampaignSessionResponse]:
    """List the sessions and lobbies of a campaign. Requires `view`."""
    return await campaigns.list_sessions(repos, campaign_id)


@router.post(
    "/{campaign_id}/sessions",
    response_model=CampaignSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session(
    campaign_id: str,
    req: CreateCampaignSessionRequest,
    principal: RunSessionCampaign,
    repos: Repos,
    spicedb: Spicedb,
    game_sessions: GameSessions,
) -> CampaignSessionResponse:
    """Create a session or staging lobby. Requires `run_session`."""
    return await campaigns.create_session(
        repos, spicedb, campaign_id, req, game_sessions, principal.user_id
    )


@router.post(
    "/{campaign_id}/sessions/reconcile-links",
    response_model=SessionLinkReconcileResponse,
)
async def reconcile_session_links(
    campaign_id: str,
    principal: RunSessionCampaign,
    repos: Repos,
    spicedb: Spicedb,
) -> SessionLinkReconcileResponse:
    """Rewrite the campaign link of every session in the campaign. Requires `run_session`."""
    return await campaigns.reconcile_session_links(repos, spicedb, campaign_id)


@router.post(
    "/{campaign_id}/roles",
    response_model=RoleAssignedResponse,
)
async def assign_role(
    campaign_id: str,
    req: AssignRoleRequest,
    principal: ManageCampaign,
    repos: Repos,
    spicedb: Spicedb,
) -> RoleAssignedResponse:
    """Grant a campaign role (dungeon_master, game_master, player, spectator). Requires `manage`."""
    return await roles.assign_role(repos, spicedb, campaign_id, req)


@router.get("/{campaign_id}/capabilities", response_model=CampaignCapabilitiesResponse)
async def get_capabilities(
    campaign_id: str,
    principal: CallerPrincipal,
    spicedb: Spicedb,
) -> CampaignCapabilitiesResponse:
    """Report which campaign actions the caller holds. Non-members receive all false."""
    return await roles.capabilities(spicedb, campaign_id, principal.user_id)
