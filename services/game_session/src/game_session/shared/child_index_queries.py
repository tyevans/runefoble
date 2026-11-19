"""Read and write the durable child indexes behind the game session lists (TASK-0567).

Writes link a child after its own aggregate is saved. Reads return child ids in link
order. A missing index stream means no children. A store error propagates to the caller.
"""

from __future__ import annotations

from game_session.shared.child_index import ChildIndexAggregate, child_index_stream_id
from runefoble_platform.aggregate_loading import load_if_exists, load_or_create
from runefoble_platform.event_sourcing import AggregateRepository, create_aggregate_repository
from runefoble_platform.lazy_repository import LazyRepository

child_index_repository = LazyRepository(lambda: create_aggregate_repository(ChildIndexAggregate))


def get_child_index_repository() -> AggregateRepository[ChildIndexAggregate]:
    """Return the repository of the child index streams."""
    return child_index_repository.get()


async def link_child(kind: str, parent_id: str, child_id: str) -> None:
    """Save the link from one parent to one child."""
    repo = get_child_index_repository()
    stream_id = child_index_stream_id(kind, parent_id)
    index = await load_or_create(repo, stream_id, ChildIndexAggregate)
    index.link(kind, parent_id, child_id)
    await repo.save(index)


async def list_child_ids(kind: str, parent_id: str) -> list[str]:
    """Return the child ids linked to one parent, in link order."""
    index = await load_if_exists(
        get_child_index_repository(), child_index_stream_id(kind, parent_id)
    )
    return [] if index is None else list(index.state.child_ids)


__all__ = [
    "child_index_repository",
    "get_child_index_repository",
    "link_child",
    "list_child_ids",
]
