"""Campaign use cases: create, read, update, list viewable, and campaign sessions.

Each mutating use case saves its aggregate first, then writes SpiceDB tuples (ADR-0001).
"""

from __future__ import annotations

import logging
from uuid import UUID, uuid4

from game_session.campaign.campaign_aggregate import CampaignAggregate, CampaignState
from game_session.campaign.errors import CampaignNotFoundError
from game_session.campaign.membership_aggregate import MembershipAggregate
from game_session.campaign.permission_flags import campaign_permissions
from game_session.campaign.repositories import (
    CampaignRepositories,
    load_or_none,
    save_aggregate,
)
from game_session.campaign.schemas import (
    CampaignPermissionsResponse,
    CampaignSessionResponse,
    CampaignSummaryResponse,
    CreateCampaignRequest,
    CreateCampaignSessionRequest,
    UpdateCampaignRequest,
)
from game_session.campaign.session_aggregate import CampaignSessionsAggregate
from game_session.campaign.tuples import SpiceDB, grant_owner, link_session
from runefoble_platform.identifiers import parse_uuid

logger = logging.getLogger("runefoble.game_session.campaign")

SEEDED_SESSION_TITLE = "Session #1: Staging Lobby"
SEEDED_SESSION_DESCRIPTION = "Initial campaign staging lobby."
ROLE_CHECKS: tuple[tuple[str, str], ...] = (
    ("manage", "owner"),
    ("run_session", "dungeon_master"),
    ("play", "player"),
    ("view", "spectator"),
)


def parse_campaign_id(raw: str) -> UUID:
    return parse_uuid(raw, field="campaign_id")


async def load_campaign(repos: CampaignRepositories, campaign_id: UUID) -> CampaignAggregate:
    campaign = await load_or_none(repos.campaigns, campaign_id)
    if campaign is None:
        raise CampaignNotFoundError(f"Campaign {campaign_id} does not exist")
    return campaign


async def load_memberships(repos: CampaignRepositories, campaign_id: UUID) -> MembershipAggregate:
    memberships = await load_or_none(repos.memberships, campaign_id)
    return memberships if memberships is not None else repos.memberships.create_new(campaign_id)


async def load_sessions(
    repos: CampaignRepositories, campaign_id: UUID
) -> CampaignSessionsAggregate:
    sessions = await load_or_none(repos.sessions, campaign_id)
    return sessions if sessions is not None else repos.sessions.create_new(campaign_id)


async def role_for(spicedb: SpiceDB, campaign_id: str, user_id: str) -> str | None:
    """Return the highest role the user holds, read from SpiceDB permissions."""
    for permission, role in ROLE_CHECKS:
        if await spicedb.check_permission("campaign", campaign_id, permission, "user", user_id):
            return role
    return None


def summary_from_state(
    state: CampaignState,
    role: str | None,
    member_count: int,
    permissions: CampaignPermissionsResponse,
) -> CampaignSummaryResponse:
    return CampaignSummaryResponse(
        id=state.campaign_id,
        title=state.title,
        description=state.description,
        setting=state.setting,
        system=state.system,
        status=state.status,
        owner_id=state.owner_id,
        role=role,
        permissions=permissions,
        member_count=member_count,
        cover_image_url=state.cover_image_url,
        settings=state.settings,
        created_at=state.created_at,
        updated_at=state.updated_at,
    )


async def _summarize(
    repos: CampaignRepositories, spicedb: SpiceDB, campaign: CampaignAggregate, user_id: str
) -> CampaignSummaryResponse:
    campaign_id = UUID(campaign.state.campaign_id)
    memberships = await load_memberships(repos, campaign_id)
    role = await role_for(spicedb, campaign.state.campaign_id, user_id)
    permissions = await campaign_permissions(spicedb, campaign.state.campaign_id, user_id)
    return summary_from_state(campaign.state, role, 1 + len(memberships.state.members), permissions)


async def create_campaign(
    repos: CampaignRepositories,
    spicedb: SpiceDB,
    owner_id: str,
    req: CreateCampaignRequest,
) -> CampaignSummaryResponse:
    campaign_id = uuid4()
    campaign = repos.campaigns.create_new(campaign_id)
    campaign.create(
        title=req.title,
        owner_id=owner_id,
        description=req.description,
        setting=req.setting,
        system=req.system,
        cover_image_url=req.cover_image_url,
        settings=req.settings,
    )
    await save_aggregate(repos.campaigns, campaign)

    seeded_session_id: str | None = None
    if req.seed_initial_session:
        sessions = repos.sessions.create_new(campaign_id)
        seeded_session_id = f"session-{uuid4().hex}"
        sessions.add_session(
            session_id=seeded_session_id,
            title=SEEDED_SESSION_TITLE,
            status="lobby",
            scheduled_at=None,
            description=SEEDED_SESSION_DESCRIPTION,
        )
        await save_aggregate(repos.sessions, sessions)

    await grant_owner(spicedb, str(campaign_id), owner_id)
    if seeded_session_id is not None:
        await link_session(spicedb, seeded_session_id, str(campaign_id))
    permissions = await campaign_permissions(spicedb, str(campaign_id), owner_id)
    return summary_from_state(campaign.state, "owner", 1, permissions)


async def get_campaign(
    repos: CampaignRepositories, spicedb: SpiceDB, campaign_id: str, user_id: str
) -> CampaignSummaryResponse:
    campaign = await load_campaign(repos, parse_campaign_id(campaign_id))
    return await _summarize(repos, spicedb, campaign, user_id)


async def update_campaign(
    repos: CampaignRepositories,
    spicedb: SpiceDB,
    campaign_id: str,
    req: UpdateCampaignRequest,
    user_id: str,
) -> CampaignSummaryResponse:
    campaign = await load_campaign(repos, parse_campaign_id(campaign_id))
    campaign.update(req.model_dump(exclude_none=True))
    await save_aggregate(repos.campaigns, campaign)
    return await _summarize(repos, spicedb, campaign, user_id)


async def list_viewable_campaigns(
    repos: CampaignRepositories, spicedb: SpiceDB, user_id: str
) -> list[CampaignSummaryResponse]:
    """List campaigns where SpiceDB grants the caller `view`. Aggregates supply the details."""
    campaign_ids = await spicedb.lookup_resources("campaign", "view", "user", user_id)
    summaries: list[CampaignSummaryResponse] = []
    for raw_id in sorted(campaign_ids):
        try:
            campaign_uuid = UUID(raw_id)
        except ValueError:
            logger.warning("SpiceDB grants view on non-UUID campaign id %s. Skipped.", raw_id)
            continue
        campaign = await load_or_none(repos.campaigns, campaign_uuid)
        if campaign is None:
            logger.warning("SpiceDB grants view on campaign %s with no campaign record", raw_id)
            continue
        summaries.append(await _summarize(repos, spicedb, campaign, user_id))
    return summaries


async def list_sessions(
    repos: CampaignRepositories, campaign_id: str
) -> list[CampaignSessionResponse]:
    cid = parse_campaign_id(campaign_id)
    await load_campaign(repos, cid)
    sessions = await load_sessions(repos, cid)
    return [
        CampaignSessionResponse(
            id=record.id,
            campaign_id=str(cid),
            title=record.title,
            status=record.status,
            scheduled_at=record.scheduled_at,
            created_at=record.created_at,
        )
        for record in sessions.state.sessions
    ]


async def create_session(
    repos: CampaignRepositories,
    spicedb: SpiceDB,
    campaign_id: str,
    req: CreateCampaignSessionRequest,
) -> CampaignSessionResponse:
    cid = parse_campaign_id(campaign_id)
    await load_campaign(repos, cid)
    sessions = await load_sessions(repos, cid)
    session_id = f"session-{uuid4().hex}"
    sessions.add_session(
        session_id=session_id,
        title=req.title,
        status=req.status,
        scheduled_at=req.scheduled_at,
        description=req.description,
    )
    await save_aggregate(repos.sessions, sessions)
    await link_session(spicedb, session_id, str(cid))
    record = sessions.state.sessions[-1]
    return CampaignSessionResponse(
        id=record.id,
        campaign_id=str(cid),
        title=record.title,
        status=record.status,
        scheduled_at=record.scheduled_at,
        created_at=record.created_at,
    )
