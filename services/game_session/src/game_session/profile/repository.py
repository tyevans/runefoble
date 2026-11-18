"""Repository access for the user profile aggregate. Built on the platform event store (ADR-0015 f)."""

from __future__ import annotations

from game_session.profile.aggregate import UserProfileAggregate, profile_stream_id
from runefoble_platform.event_sourcing import (
    AggregateRepository,
    create_aggregate_repository,
    get_event_store,
)


def get_profile_repository() -> AggregateRepository[UserProfileAggregate]:
    """Bind the repository to the process event store on each call, so no state is cached."""
    return create_aggregate_repository(UserProfileAggregate, event_store=get_event_store())


async def load_profile(
    repo: AggregateRepository[UserProfileAggregate], subject: str
) -> UserProfileAggregate:
    """Load the subject's profile stream. A subject with no edits gets an empty aggregate."""
    return await repo.load_or_create(profile_stream_id(subject))
