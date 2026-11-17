"""Aggregate repositories for the campaign lifecycle, built on the platform event store.

No state is kept in process memory. Every read goes through the event store, so a
restarted service sees the same campaigns, members, and invites (ADR-0015 f).
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from eventsource.domain.exceptions import AggregateNotFoundError
from eventsource.domain.exceptions import OptimisticLockError as _OptimisticLockError
from eventsource.ports.store import FullEventStore
from game_session.campaign.campaign_aggregate import CampaignAggregate
from game_session.campaign.errors import ConcurrentUpdateError
from game_session.campaign.invite_aggregate import InviteAggregate
from game_session.campaign.membership_aggregate import MembershipAggregate
from game_session.campaign.session_aggregate import CampaignSessionsAggregate
from runefoble_platform.event_sourcing import (
    AggregateRepository,
    create_aggregate_repository,
    get_event_store,
)


@dataclass(frozen=True)
class CampaignRepositories:
    campaigns: AggregateRepository[CampaignAggregate]
    memberships: AggregateRepository[MembershipAggregate]
    invites: AggregateRepository[InviteAggregate]
    sessions: AggregateRepository[CampaignSessionsAggregate]


def build_campaign_repositories(store: FullEventStore) -> CampaignRepositories:
    """Bind every campaign aggregate repository to one event store."""
    return CampaignRepositories(
        campaigns=create_aggregate_repository(CampaignAggregate, event_store=store),
        memberships=create_aggregate_repository(MembershipAggregate, event_store=store),
        invites=create_aggregate_repository(InviteAggregate, event_store=store),
        sessions=create_aggregate_repository(CampaignSessionsAggregate, event_store=store),
    )


_repositories: CampaignRepositories | None = None


def get_campaign_repositories() -> CampaignRepositories:
    global _repositories
    if _repositories is None:
        _repositories = build_campaign_repositories(get_event_store())
    return _repositories


def set_campaign_repositories(repos: CampaignRepositories | None) -> None:
    """Replace the repositories. Tests use this to bind a fresh process to a store."""
    global _repositories
    _repositories = repos


async def save_aggregate[T](repo: AggregateRepository[T], aggregate: T) -> None:
    """Save an aggregate. A version conflict becomes a 409 for the caller to retry."""
    try:
        await repo.save(aggregate)  # type: ignore[arg-type]
    except _OptimisticLockError as exc:
        raise ConcurrentUpdateError("The campaign changed while this request ran. Retry.") from exc


async def load_or_none[T](repo: AggregateRepository[T], aggregate_id: UUID) -> T | None:
    """Load an aggregate. Return None when its stream has no events."""
    try:
        return await repo.load(aggregate_id)
    except AggregateNotFoundError:
        return None
