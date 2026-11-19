"""Child index kind and list query of the mercenary bounty board (TASK-0567, ADR-0021 D2).

The kind value is part of the index stream ids. Do not change it.
"""

from __future__ import annotations

from game_session.shared.child_index_queries import list_child_ids

SESSION_BOUNTIES = "session_bounties"


async def list_bounties_for_session(session_id: str) -> list[str]:
    """Return the bounty ids posted to one session."""
    return await list_child_ids(SESSION_BOUNTIES, session_id)


__all__ = ["SESSION_BOUNTIES", "list_bounties_for_session"]
