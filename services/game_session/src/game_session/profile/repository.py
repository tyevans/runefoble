"""Repository access for the user profile aggregate. Built on the platform event store (ADR-0015 f)."""

from __future__ import annotations

from game_session.profile.aggregate import UserProfileAggregate, profile_stream_id
from runefoble_platform.event_sourcing import AggregateRepository, create_aggregate_repository


def get_profile_repository() -> AggregateRepository[UserProfileAggregate]:
    """Build the repository. It resolves the process event store per operation."""
    return create_aggregate_repository(UserProfileAggregate)


async def load_profile(
    repo: AggregateRepository[UserProfileAggregate], subject: str
) -> UserProfileAggregate:
    """Load the subject's profile stream. A subject with no edits gets an empty aggregate."""
    return await repo.load_or_create(profile_stream_id(subject))
