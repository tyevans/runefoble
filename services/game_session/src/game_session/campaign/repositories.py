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
from runefoble_platform.event_sourcing import (
    AggregateRepository,
    create_aggregate_repository,
)


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


_repositories: CampaignRepositories | None = None


def get_campaign_repositories() -> CampaignRepositories:
    global _repositories
    if _repositories is None:
        _repositories = build_campaign_repositories()
    return _repositories


def set_campaign_repositories(repos: CampaignRepositories | None) -> None:
    """Replace the repositories. Tests use this to bind a fresh process to a store."""
    global _repositories
    _repositories = repos


def concurrent_update() -> ConcurrentUpdateError:
    """The error for a campaign save that lost an optimistic lock. The caller retries."""
    return ConcurrentUpdateError("The campaign changed while this request ran. Retry.")
