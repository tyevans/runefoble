"""Aggregate repositories for the campaign lifecycle, built on the platform event store.

No state is kept in process memory. Every read goes through the event store, so a
restarted service sees the same campaigns, members, and invites (ADR-0015 f).
"""

from __future__ import annotations

from dataclasses import dataclass

from game_session.campaign.campaign_aggregate import CampaignAggregate
from game_session.campaign.errors import ConcurrentUpdateError
from game_session.campaign.invite_aggregate import InviteAggregate
from game_session.campaign.membership_aggregate import MembershipAggregate
from game_session.campaign.session_aggregate import CampaignSessionsAggregate
from game_session.shared.container_access import app_container
from runefoble_platform.event_sourcing import (
    AggregateRepository,
    create_aggregate_repository,
)
from starlette.requests import HTTPConnection


@dataclass(frozen=True)
class CampaignRepositories:
    campaigns: AggregateRepository[CampaignAggregate]
    memberships: AggregateRepository[MembershipAggregate]
    invites: AggregateRepository[InviteAggregate]
    sessions: AggregateRepository[CampaignSessionsAggregate]


def build_campaign_repositories() -> CampaignRepositories:
    """Build every campaign aggregate repository. Each resolves the event store per operation."""
    return CampaignRepositories(
        campaigns=create_aggregate_repository(CampaignAggregate),
        memberships=create_aggregate_repository(MembershipAggregate),
        invites=create_aggregate_repository(InviteAggregate),
        sessions=create_aggregate_repository(CampaignSessionsAggregate),
    )


def campaign_repositories(conn: HTTPConnection) -> CampaignRepositories:
    """Return the campaign repositories of the app container (ADR-0021 D6 rule 4)."""
    return app_container(conn).campaign


def concurrent_update() -> ConcurrentUpdateError:
    """The error for a campaign save that lost an optimistic lock. The caller retries."""
    return ConcurrentUpdateError("The campaign changed while this request ran. Retry.")
