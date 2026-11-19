"""Unit tests for the aggregate loading helpers in runefoble_platform (TASK-0561).

Only "aggregate not found" may create a new aggregate. A store outage raises to the caller and
is never a missing aggregate. These helpers have no HTTP route of their own. The route-driven
outage cases live in tests/test_blackbox_aggregate_load_errors.py.

Governed by ADR-0011 (eventsource-py) and ADR-0015 (fail closed).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from eventsource.adapters.memory.store import InMemoryEventStore
from eventsource.domain.exceptions import OptimisticLockError
from fastapi import HTTPException
from runefoble_platform.aggregate_loading import (
    load_if_exists,
    load_or_404,
    load_or_create,
    save_or_conflict,
)
from runefoble_platform.event_sourcing import create_aggregate_repository
from runefoble_platform.lazy_repository import LazyRepository
from soundscape.aggregate import SoundscapeAggregate

from tests.helpers.event_store_seam import OutageEventStore


@pytest.mark.asyncio
async def test_unit_load_or_create_creates_only_when_stream_is_absent() -> None:
    """An unknown id yields a new aggregate. A known id yields the stored history."""
    repo = create_aggregate_repository(SoundscapeAggregate, event_store=InMemoryEventStore())
    agg_id = uuid4()

    fresh = await load_or_create(repo, agg_id, SoundscapeAggregate)
    assert fresh.version == 0
    fresh.record_tension_update(
        session_id="s-helper",
        tension_score=42,
        stem_profile="explore",
        combat_round=1,
        enemy_cr_balance=1.0,
        lowest_health_ratio=1.0,
    )
    await repo.save(fresh)

    loaded = await load_or_create(repo, agg_id, SoundscapeAggregate)
    assert loaded.state.tension_score == 42


@pytest.mark.asyncio
async def test_unit_load_helpers_propagate_store_errors() -> None:
    """A store outage raises to the caller. It is not treated as a missing aggregate."""
    repo = create_aggregate_repository(SoundscapeAggregate, event_store=OutageEventStore())
    agg_id = uuid4()

    with pytest.raises(ConnectionError):
        await load_or_create(repo, agg_id, SoundscapeAggregate)
    with pytest.raises(ConnectionError):
        await load_if_exists(repo, agg_id)


@pytest.mark.asyncio
async def test_unit_load_if_exists_returns_none_for_unknown_stream() -> None:
    """A read of an unknown id reports absence, not an error."""
    repo = create_aggregate_repository(SoundscapeAggregate, event_store=InMemoryEventStore())
    assert await load_if_exists(repo, uuid4()) is None


@pytest.mark.asyncio
async def test_unit_load_or_404_raises_404_with_detail_for_unknown_stream() -> None:
    """A missing stream answers 404 with the caller's detail text."""
    repo = create_aggregate_repository(SoundscapeAggregate, event_store=InMemoryEventStore())

    with pytest.raises(HTTPException) as caught:
        await load_or_404(repo, uuid4(), "Soundscape not found")
    assert caught.value.status_code == 404
    assert caught.value.detail == "Soundscape not found"


@pytest.mark.asyncio
async def test_unit_load_or_404_returns_stored_aggregate() -> None:
    repo = create_aggregate_repository(SoundscapeAggregate, event_store=InMemoryEventStore())
    agg_id = uuid4()
    fresh = SoundscapeAggregate(agg_id)
    fresh.record_tension_update(
        session_id="s-404",
        tension_score=7,
        stem_profile="explore",
        combat_round=1,
        enemy_cr_balance=1.0,
        lowest_health_ratio=1.0,
    )
    await repo.save(fresh)

    loaded = await load_or_404(repo, agg_id, "unused")
    assert loaded.state.tension_score == 7


@pytest.mark.asyncio
async def test_unit_load_or_404_propagates_store_errors() -> None:
    """A store outage is never a 404."""
    repo = create_aggregate_repository(SoundscapeAggregate, event_store=OutageEventStore())

    with pytest.raises(ConnectionError):
        await load_or_404(repo, uuid4(), "unused")


@pytest.mark.asyncio
async def test_unit_save_or_conflict_maps_version_conflict_to_the_chosen_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A lock failure becomes the error that the caller supplies."""
    repo = create_aggregate_repository(SoundscapeAggregate, event_store=InMemoryEventStore())
    agg_id = uuid4()
    aggregate = SoundscapeAggregate(agg_id)

    async def conflicting_save(_aggregate: SoundscapeAggregate) -> None:
        raise OptimisticLockError(agg_id, expected_version=0, actual_version=1)

    monkeypatch.setattr(repo, "save", conflicting_save)
    with pytest.raises(HTTPException) as caught:
        await save_or_conflict(
            repo,
            aggregate,
            lambda: HTTPException(status_code=409, detail="changed"),
        )
    assert caught.value.status_code == 409
    assert caught.value.detail == "changed"


@pytest.mark.asyncio
async def test_unit_save_or_conflict_saves_without_conflict() -> None:
    repo = create_aggregate_repository(SoundscapeAggregate, event_store=InMemoryEventStore())
    agg_id = uuid4()
    aggregate = SoundscapeAggregate(agg_id)
    aggregate.record_tension_update(
        session_id="s-save",
        tension_score=3,
        stem_profile="explore",
        combat_round=1,
        enemy_cr_balance=1.0,
        lowest_health_ratio=1.0,
    )

    await save_or_conflict(repo, aggregate, lambda: RuntimeError("must not fire"))
    assert await load_if_exists(repo, agg_id) is not None


def test_unit_lazy_repository_builds_once_and_set_replaces_it() -> None:
    """`get` builds the repository on first use and returns the same one afterwards."""
    built: list[object] = []

    def factory():
        repo = create_aggregate_repository(SoundscapeAggregate, event_store=InMemoryEventStore())
        built.append(repo)
        return repo

    lazy = LazyRepository(factory)
    assert built == []
    first = lazy.get()
    assert lazy.get() is first
    assert len(built) == 1

    replacement = create_aggregate_repository(SoundscapeAggregate, event_store=InMemoryEventStore())
    lazy.set(replacement)
    assert lazy.get() is replacement

    lazy.set(None)
    assert lazy.get() is not replacement
    assert len(built) == 2
