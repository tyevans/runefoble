"""The event store seam for tests: a fresh store per test, and a store outage on demand.

Tests change the process event store only through the provider frontdoor,
`runefoble_platform.event_sourcing.set_event_store`. No test patches a store class.
Repositories resolve the store per operation, so a swap is visible to every service route.

Governed by ADR-0011, ADR-0015 and Hard Invariant 7 (TASK-0773).
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import NoReturn

import pytest
from eventsource.adapters.memory.store import InMemoryEventStore
from eventsource.domain.stream_id import StreamId
from runefoble_platform.event_sourcing import get_event_store, set_event_store

from tests.helpers.module_state import restored_seam


class OutageEventStore(InMemoryEventStore):
    """An event store whose reads fail, as when PostgreSQL is unreachable at request time."""

    def read_stream(self, *_args: object, **_kwargs: object) -> NoReturn:  # type: ignore[override]
        raise ConnectionError("event store unreachable")


class AppendOutageStore:
    """Delegate every call to the inner store, except appends to one stream category.

    An append to that category raises, as when PostgreSQL rejects a write. Reads still work,
    so the events already stored remain visible.
    """

    def __init__(self, inner: object, stream_category: str) -> None:
        self._inner = inner
        self._category = stream_category

    def __getattr__(self, name: str) -> object:
        return getattr(self._inner, name)

    async def append(self, stream: StreamId, events: Sequence[object], expected: object) -> object:
        if stream.category == self._category:
            raise ConnectionError("event store unreachable")
        return await self._inner.append(stream, events, expected)  # type: ignore[attr-defined]


@contextmanager
def store_append_outage(stream_category: str) -> Iterator[None]:
    """Fail every append to one stream category, then restore the previous store.

    Use it to fail the second of two saves, for example the character save after the crafting
    save. The previous store keeps its events.
    """
    previous = get_event_store()
    set_event_store(AppendOutageStore(previous, stream_category))  # type: ignore[arg-type]
    try:
        yield
    finally:
        set_event_store(previous)


@contextmanager
def store_outage() -> Iterator[None]:
    """Route every event store read to an unreachable store, then restore the previous store.

    The previous store keeps its events, so a read after the block sees the stored history.
    """
    previous = get_event_store()
    set_event_store(OutageEventStore())
    try:
        yield
    finally:
        set_event_store(previous)


@pytest.fixture(autouse=True)
def default_event_store() -> Iterator[InMemoryEventStore]:
    """Give each test a fresh in-memory store through the seam, and restore the previous one."""
    previous = get_event_store()
    store = InMemoryEventStore()
    set_event_store(store)
    try:
        yield store
    finally:
        set_event_store(previous)


@pytest.fixture
def reset_event_store() -> Iterator[None]:
    """Unset the process event store for one test, so the settings default builds the next store.

    A test that restarts a durable store requests this fixture with
    `pytest.mark.usefixtures("reset_event_store")`. The previous store is restored afterwards.
    """
    with restored_seam(get_event_store, set_event_store, None, replace=True):
        yield
