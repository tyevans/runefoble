"""Read and write the durable child indexes behind the game session lists (TASK-0567).

Writes link a child after its own aggregate is saved. Reads return child ids in link
order. A missing index stream means no children. A store error propagates to the caller.
"""

from __future__ import annotations

from uuid import UUID

from game_session.child_index import (
    ChildIndexAggregate,
    ChildIndexKind,
    child_index_stream_id,
)
from game_session.dependencies import get_child_index_repository
from runefoble_platform.aggregate_loading import load_if_exists, load_or_create


async def link_child(kind: ChildIndexKind, parent_id: str, child_id: str) -> None:
    """Save the link from one parent to one child."""
    repo = get_child_index_repository()
    stream_id = child_index_stream_id(kind, parent_id)
    index = await load_or_create(repo, stream_id, ChildIndexAggregate)
    index.link(kind, parent_id, child_id)
    await repo.save(index)


async def list_child_ids(kind: ChildIndexKind, parent_id: str) -> list[str]:
    """Return the child ids linked to one parent, in link order."""
    index = await load_if_exists(
        get_child_index_repository(), child_index_stream_id(kind, parent_id)
    )
    return [] if index is None else list(index.state.child_ids)


async def list_bounties_for_session(session_id: str) -> list[str]:
    """Return the bounty ids posted to one session."""
    return await list_child_ids(ChildIndexKind.SESSION_BOUNTIES, session_id)


async def list_world_contracts_for_world(shared_world_id: str | UUID) -> list[str]:
    """Return the caravan contract ids posted to one shared world."""
    return await list_child_ids(ChildIndexKind.WORLD_CONTRACTS, str(shared_world_id))


async def list_establishments_for_settlement(settlement_id: str) -> list[str]:
    """Return the establishment ids built in one settlement."""
    return await list_child_ids(ChildIndexKind.SETTLEMENT_ESTABLISHMENTS, settlement_id)


async def list_settlements_for_campaign(campaign_id: str) -> list[str]:
    """Return the settlement ids founded for one campaign."""
    return await list_child_ids(ChildIndexKind.CAMPAIGN_SETTLEMENTS, campaign_id)


async def list_workers_for_establishment(establishment_id: str) -> list[str]:
    """Return the NPC worker ids assigned to one establishment."""
    return await list_child_ids(ChildIndexKind.ESTABLISHMENT_WORKERS, establishment_id)


__all__ = [
    "link_child",
    "list_bounties_for_session",
    "list_child_ids",
    "list_establishments_for_settlement",
    "list_settlements_for_campaign",
    "list_workers_for_establishment",
    "list_world_contracts_for_world",
]
