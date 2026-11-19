"""Open a game session for a campaign: one call writes the aggregate and its campaign link.

The aggregate id is the session id that every campaign and game session route uses (TASK-0706).
The aggregate is saved first, then the campaign link is written (ADR-0001).
"""

from __future__ import annotations

from uuid import UUID, uuid4

from eventsource.application.aggregates.repository import AggregateRepository
from game_session.aggregate import GameSessionAggregate
from game_session.campaign.tuples import SpiceDB, link_session


async def open_game_session(
    repo: AggregateRepository[GameSessionAggregate],
    spicedb: SpiceDB,
    campaign_id: UUID,
    *,
    title: str,
    dm_id: str,
) -> GameSessionAggregate:
    """Create the GameSession aggregate with a new UUID and link it to the campaign."""
    session = GameSessionAggregate(uuid4())
    session.create(campaign_id=campaign_id, title=title, dm_id=dm_id)
    await repo.save(session)
    await link_session(spicedb, str(session.aggregate_id), str(campaign_id))
    return session
