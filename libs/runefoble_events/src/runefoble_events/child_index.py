"""Index event that links a parent id to a child aggregate id.

Owned by the game_session bounded context (TASK-0567). The event is internal to the
session service. It is saved to the event store and is not published to a bus.
"""

from __future__ import annotations

from typing import ClassVar

from runefoble_events.base import BaseRunefobleEvent, register_event


@register_event("runefoble.events.game_session.child_linked")
class ChildLinked(BaseRunefobleEvent):
    """Fired when a child aggregate (bounty, settlement, worker, and so on) is linked to its parent."""

    suppress_event_type_warning: ClassVar[bool] = True
    event_type: str = "runefoble.events.game_session.child_linked"

    aggregate_type: str = "ChildIndex"
    index_kind: str
    parent_id: str
    child_id: str


__all__ = ["ChildLinked"]
