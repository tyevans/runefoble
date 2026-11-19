"""Read and write the durable child indexes behind the game session lists (TASK-0567).

Writes link a child after its own aggregate is saved. Reads return child ids in link
order. A missing index stream means no children. A store error propagates to the caller.
The app container holds the index repository (ADR-0021 D6 rule 5).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from game_session.shared.child_index import ChildIndexAggregate, child_index_stream_id
from game_session.shared.container_access import app_container
from runefoble_platform.aggregate_loading import load_if_exists, load_or_create
from runefoble_platform.event_sourcing import AggregateRepository, create_aggregate_repository
from starlette.requests import HTTPConnection


def build_child_index_repository() -> AggregateRepository[ChildIndexAggregate]:
    """Build the repository of the child index streams. It resolves the store per operation."""
    return create_aggregate_repository(ChildIndexAggregate)


def child_index_repository(conn: HTTPConnection) -> AggregateRepository[ChildIndexAggregate]:
    """Return the child index repository of the app container."""
    return app_container(conn).child_indexes


ChildIndexes = Annotated[AggregateRepository[ChildIndexAggregate], Depends(child_index_repository)]


async def link_child(
    repo: AggregateRepository[ChildIndexAggregate], kind: str, parent_id: str, child_id: str
) -> None:
    """Save the link from one parent to one child."""
    stream_id = child_index_stream_id(kind, parent_id)
    index = await load_or_create(repo, stream_id, ChildIndexAggregate)
    index.link(kind, parent_id, child_id)
    await repo.save(index)


async def list_child_ids(
    repo: AggregateRepository[ChildIndexAggregate], kind: str, parent_id: str
) -> list[str]:
    """Return the child ids linked to one parent, in link order."""
    index = await load_if_exists(repo, child_index_stream_id(kind, parent_id))
    return [] if index is None else list(index.state.child_ids)


__all__ = [
    "ChildIndexes",
    "build_child_index_repository",
    "child_index_repository",
    "link_child",
    "list_child_ids",
]
