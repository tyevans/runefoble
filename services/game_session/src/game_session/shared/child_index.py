"""Durable parent-to-child id indexes for game session list queries (TASK-0567).

Each index is one event-sourced stream per (kind, parent id). The stream id is derived
from the kind and the parent id, so the index needs no process memory. A list query
reads the stream from the event store. A store outage raises to the caller (ADR-0015 f).

The mechanism accepts the kind as a string. Each domain package declares its own kinds
(ADR-0021 D2). The kind values do not change, so the stream ids do not change.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid5

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from pydantic import BaseModel, Field
from runefoble_events.events import ChildLinked

_INDEX_NAMESPACE = UUID("3f6c1a9e-5b8d-4f0e-9a7c-2d4e6b8f1a30")


def child_index_stream_id(kind: str, parent_id: str) -> UUID:
    """Return the deterministic stream id of the index for one parent."""
    return uuid5(_INDEX_NAMESPACE, f"{str(kind)}:{parent_id}")


class ChildIndexState(BaseModel):
    """Child ids of one parent, in link order, without duplicates."""

    index_kind: str = ""
    parent_id: str = ""
    child_ids: list[str] = Field(default_factory=list)


class ChildIndexAggregate(DeclarativeAggregate[ChildIndexState]):
    """Records which child aggregates belong to one parent."""

    aggregate_type = "ChildIndex"
    requires_creation_event = False

    def __init__(self, aggregate_id: Any = None, **kwargs: Any) -> None:
        super().__init__(aggregate_id=aggregate_id, **kwargs)
        if self._state is None:
            self._state = ChildIndexState()

    def link(self, kind: str, parent_id: str, child_id: str) -> None:
        """Link a child to the parent. Linking the same child twice emits no event."""
        if child_id in self.state.child_ids:
            return
        self.create_event(
            ChildLinked,
            index_kind=str(kind),
            parent_id=parent_id,
            child_id=child_id,
        )

    @handles(ChildLinked)
    def _on_linked(self, event: ChildLinked) -> None:
        self.state.index_kind = event.index_kind
        self.state.parent_id = event.parent_id
        if event.child_id not in self.state.child_ids:
            self.state.child_ids.append(event.child_id)


__all__ = [
    "ChildIndexAggregate",
    "ChildIndexState",
    "child_index_stream_id",
]
