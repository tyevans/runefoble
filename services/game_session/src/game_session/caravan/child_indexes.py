"""Child index kind and list query of the caravan contract board (TASK-0567, ADR-0021 D2).

The kind value is part of the index stream ids. Do not change it.
"""

from __future__ import annotations

from uuid import UUID

from game_session.shared.child_index import ChildIndexAggregate
from game_session.shared.child_index_queries import list_child_ids
from runefoble_platform.event_sourcing import AggregateRepository

WORLD_CONTRACTS = "world_contracts"


async def list_world_contracts_for_world(
    child_indexes: AggregateRepository[ChildIndexAggregate], shared_world_id: str | UUID
) -> list[str]:
    """Return the caravan contract ids posted to one shared world."""
    return await list_child_ids(child_indexes, WORLD_CONTRACTS, str(shared_world_id))


__all__ = ["WORLD_CONTRACTS", "list_world_contracts_for_world"]
