"""Index event that links a parent id to a child aggregate id.

Owned by the game_session bounded context (TASK-0567). The event is internal to the
session service. It is saved to the event store and is not published to a bus.
"""

from __future__ import annotations

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event
class ChildLinked(BaseRunefobleEvent):
    """Fired when a child aggregate (bounty, settlement, worker, and so on) is linked to its parent."""

    aggregate_type: str = "ChildIndex"
    index_kind: str
    parent_id: str
    child_id: str


__all__ = ["ChildLinked"]
