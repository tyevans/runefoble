"""Campaign use cases: create, read, update, list viewable, and campaign sessions.

Each mutating use case saves its aggregate first, then writes SpiceDB tuples (ADR-0001).
"""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID, uuid4

from eventsource.application.aggregates.repository import AggregateRepository
from game_session.aggregate import GameSessionAggregate
from game_session.campaign.campaign_aggregate import CampaignAggregate, CampaignState
from game_session.campaign.errors import CampaignNotFoundError
from game_session.campaign.membership_aggregate import MembershipAggregate
from game_session.campaign.permission_flags import (
    flags_from,
    granted_by_campaign,
    granted_permissions,
    role_from,
)
from game_session.campaign.repositories import (
    CampaignRepositories,
    concurrent_update,
)
from game_session.campaign.schemas import (
    CampaignPermissionsResponse,
    CampaignSessionResponse,
    CampaignSummaryResponse,
    CreateCampaignRequest,
    CreateCampaignSessionRequest,
    SessionLinkReconcileResponse,
    UpdateCampaignRequest,
)
from game_session.campaign.session_aggregate import CampaignSessionsAggregate
from game_session.campaign.session_bootstrap import open_game_session
from game_session.campaign.tuples import grant_owner, link_session
from runefoble_auth.port import SpiceDBPort
from runefoble_platform.aggregate_loading import load_if_exists, save_or_conflict
from runefoble_platform.identifiers import parse_uuid
from runefoble_platform.telemetry import get_tracer

logger = logging.getLogger("runefoble.game_session.campaign")
tracer = get_tracer("runefoble.game_session.campaign")

SEEDED_SESSION_TITLE = "Session #1: Staging Lobby"
SEEDED_SESSION_DESCRIPTION = "Initial campaign staging lobby."
LIST_LOAD_CONCURRENCY = 5
"""Most campaign loads that one list read runs at a time. It matches the default pool size."""


def parse_campaign_id(raw: str) -> UUID:
    return parse_uuid(raw, field="campaign_id")


async def load_campaign(repos: CampaignRepositories, campaign_id: UUID) -> CampaignAggregate:
    campaign = await load_if_exists(repos.campaigns, campaign_id)
    if campaign is None:
        raise CampaignNotFoundError(f"Campaign {campaign_id} does not exist")
    return campaign


async def load_memberships(repos: CampaignRepositories, campaign_id: UUID) -> MembershipAggregate:
    memberships = await load_if_exists(repos.memberships, campaign_id)
    return memberships if memberships is not None else repos.memberships.create_new(campaign_id)


async def load_sessions(
    repos: CampaignRepositories, campaign_id: UUID
) -> CampaignSessionsAggregate:
    sessions = await load_if_exists(repos.sessions, campaign_id)
    return sessions if sessions is not None else repos.sessions.create_new(campaign_id)


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
    repos: CampaignRepositories,
    campaign: CampaignAggregate,
    granted: frozenset[str],
) -> CampaignSummaryResponse:
    memberships = await load_memberships(repos, UUID(campaign.state.campaign_id))
    return summary_from_state(
        campaign.state,
        role_from(granted),
        1 + len(memberships.state.members),
        flags_from(granted),
    )


async def _summarize_for(
    repos: CampaignRepositories, spicedb: SpiceDBPort, campaign: CampaignAggregate, user_id: str
) -> CampaignSummaryResponse:
    granted = await granted_permissions(spicedb, campaign.state.campaign_id, user_id)
    return await _summarize(repos, campaign, granted)


async def create_campaign(
    repos: CampaignRepositories,
    spicedb: SpiceDBPort,
    owner_id: str,
    owner_username: str | None,
    req: CreateCampaignRequest,
    game_sessions: AggregateRepository[GameSessionAggregate],
) -> CampaignSummaryResponse:
    """Create a campaign. `owner_username` comes from the creator's verified token."""
    campaign_id = uuid4()
    campaign = repos.campaigns.create_new(campaign_id)
    campaign.create(
        title=req.title,
        owner_id=owner_id,
        owner_username=owner_username,
        description=req.description,
        setting=req.setting,
        system=req.system,
        cover_image_url=req.cover_image_url,
        settings=req.settings,
    )
    await save_or_conflict(repos.campaigns, campaign, concurrent_update)

    if req.seed_initial_session:
        seeded = await open_game_session(
            game_sessions,
            spicedb,
            campaign_id,
            title=SEEDED_SESSION_TITLE,
            dm_id=owner_id,
        )
        sessions = repos.sessions.create_new(campaign_id)
        sessions.add_session(
            session_id=str(seeded.aggregate_id),
            title=SEEDED_SESSION_TITLE,
            status="lobby",
            scheduled_at=None,
            description=SEEDED_SESSION_DESCRIPTION,
        )
        await save_or_conflict(repos.sessions, sessions, concurrent_update)

    await grant_owner(spicedb, str(campaign_id), owner_id)
    granted = await granted_permissions(spicedb, str(campaign_id), owner_id)
    return summary_from_state(campaign.state, "owner", 1, flags_from(granted))


async def get_campaign(
    repos: CampaignRepositories, spicedb: SpiceDBPort, campaign_id: str, user_id: str
) -> CampaignSummaryResponse:
    campaign = await load_campaign(repos, parse_campaign_id(campaign_id))
    return await _summarize_for(repos, spicedb, campaign, user_id)


async def update_campaign(
    repos: CampaignRepositories,
    spicedb: SpiceDBPort,
    campaign_id: str,
    req: UpdateCampaignRequest,
    user_id: str,
) -> CampaignSummaryResponse:
    campaign = await load_campaign(repos, parse_campaign_id(campaign_id))
    campaign.update(req.model_dump(exclude_none=True))
    await save_or_conflict(repos.campaigns, campaign, concurrent_update)
    return await _summarize_for(repos, spicedb, campaign, user_id)


async def list_viewable_campaigns(
    repos: CampaignRepositories, spicedb: SpiceDBPort, user_id: str
) -> list[CampaignSummaryResponse]:
    """List campaigns where SpiceDB grants the caller `view`. Aggregates supply the details.

    SpiceDB gets one lookup per distinct permission, whatever the campaign count. The
    campaign loads run concurrently, at most `LIST_LOAD_CONCURRENCY` at a time (TASK-0907).
    """
    with tracer.start_as_current_span("game_session.list_viewable_campaigns") as span:
        granted = await granted_by_campaign(spicedb, user_id)
        span.set_attribute("runefoble.campaign.viewable_count", len(granted))
        gate = asyncio.Semaphore(LIST_LOAD_CONCURRENCY)

        async def summarize(raw_id: str) -> CampaignSummaryResponse | None:
            async with gate:
                return await _load_summary(repos, raw_id, granted[raw_id])

        results = await asyncio.gather(*(summarize(raw_id) for raw_id in sorted(granted)))
        summaries = [summary for summary in results if summary is not None]
        span.set_attribute("runefoble.campaign.listed_count", len(summaries))
        return summaries


async def _load_summary(
    repos: CampaignRepositories, raw_id: str, granted: frozenset[str]
) -> CampaignSummaryResponse | None:
    """Summarize one listed campaign. Skip an id with no campaign record, and log it."""
    try:
        campaign_uuid = UUID(raw_id)
    except ValueError:
        logger.warning("SpiceDB grants view on non-UUID campaign id %s. Skipped.", raw_id)
        return None
    campaign = await load_if_exists(repos.campaigns, campaign_uuid)
    if campaign is None:
        logger.warning("SpiceDB grants view on campaign %s with no campaign record", raw_id)
        return None
    return await _summarize(repos, campaign, granted)


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


async def reconcile_session_links(
    repos: CampaignRepositories, spicedb: SpiceDBPort, campaign_id: str
) -> SessionLinkReconcileResponse:
    """Write the campaign link for every session of a campaign.

    The link write is idempotent. A session that already has its link is written again with
    the same tuple. Use this to repair a campaign whose sessions predate `game_session#campaign`.
    """
    cid = parse_campaign_id(campaign_id)
    await load_campaign(repos, cid)
    sessions = await load_sessions(repos, cid)
    for record in sessions.state.sessions:
        await link_session(spicedb, record.id, str(cid))
    return SessionLinkReconcileResponse(campaign_id=str(cid), linked=len(sessions.state.sessions))


async def create_session(
    repos: CampaignRepositories,
    spicedb: SpiceDBPort,
    campaign_id: str,
    req: CreateCampaignSessionRequest,
    game_sessions: AggregateRepository[GameSessionAggregate],
    caller_id: str,
) -> CampaignSessionResponse:
    """Create the campaign session entry and its game session under one id (TASK-0706)."""
    cid = parse_campaign_id(campaign_id)
    await load_campaign(repos, cid)
    sessions = await load_sessions(repos, cid)
    game_session = await open_game_session(
        game_sessions, spicedb, cid, title=req.title, dm_id=caller_id
    )
    sessions.add_session(
        session_id=str(game_session.aggregate_id),
        title=req.title,
        status=req.status,
        scheduled_at=req.scheduled_at,
        description=req.description,
    )
    await save_or_conflict(repos.sessions, sessions, concurrent_update)
    record = sessions.state.sessions[-1]
    return CampaignSessionResponse(
        id=record.id,
        campaign_id=str(cid),
        title=record.title,
        status=record.status,
        scheduled_at=record.scheduled_at,
        created_at=record.created_at,
    )
