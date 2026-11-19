"""Blackbox tests: aggregate load errors surface as 503, never as empty aggregates (TASK-0561).

Governed by ADR-0011 (eventsource-py), ADR-0015 (fail closed) and Hard Invariant 7.
Only "aggregate not found" may create a new aggregate. A store outage must not create a
stream with an existing aggregate id, and must not return canned data.

The store double wraps the process event store and raises a connection error on reads. It
sits at the store boundary. The code under test is not mocked.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from uuid import uuid4

import pytest
from eventsource.adapters.memory.store import InMemoryEventStore
from eventsource.domain.exceptions import OptimisticLockError
from fastapi import HTTPException
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from runefoble_platform.aggregate_loading import (
    load_if_exists,
    load_or_404,
    load_or_create,
    save_or_conflict,
)
from runefoble_platform.event_sourcing import create_aggregate_repository
from runefoble_platform.lazy_repository import LazyRepository
from soundscape.aggregate import SoundscapeAggregate
from soundscape.main import app

from tests.helpers.event_store_seam import store_outage
from tests.helpers.ws_identity import bearer

TENSION_URL = "/api/v1/soundscape/tension"
CALCULATE_URL = "/api/v1/soundscape/tension/calculate"


def _connection_refused(*_args: object, **_kwargs: object) -> None:
    raise ConnectionError("event store unreachable")


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, headers=bearer("soundscape-tester"))


@pytest.fixture
def owned_session_id(trusted_ws_issuer, game_session_upstream) -> str:
    """Create a campaign and a session through the gateway frontdoor. The test subject owns both."""
    headers = bearer("soundscape-tester")
    with TestClient(gateway_app) as gateway:
        campaign = gateway.post(
            "/api/v1/campaigns",
            json={"title": "Outage Vault", "setting": "Underdark"},
            headers=headers,
        )
        assert campaign.status_code == 201, campaign.text
        session = gateway.post(
            f"/api/v1/campaigns/{campaign.json()['id']}/sessions",
            json={"title": "Store Outage"},
            headers=headers,
        )
        assert session.status_code == 201, session.text
        return session.json()["id"]


def test_load_or_create_creates_only_when_stream_is_absent() -> None:
    """An unknown id yields a new aggregate. A known id yields the stored history."""
    repo = create_aggregate_repository(SoundscapeAggregate, event_store=InMemoryEventStore())
    agg_id = uuid4()

    fresh = _run(load_or_create(repo, agg_id, SoundscapeAggregate))
    assert fresh.version == 0
    fresh.record_tension_update(
        session_id="s-helper",
        tension_score=42,
        stem_profile="explore",
        combat_round=1,
        enemy_cr_balance=1.0,
        lowest_health_ratio=1.0,
    )
    _run(repo.save(fresh))

    loaded = _run(load_or_create(repo, agg_id, SoundscapeAggregate))
    assert loaded.state.tension_score == 42


def test_load_helpers_propagate_store_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """A store outage raises to the caller. It is not treated as a missing aggregate."""
    store = InMemoryEventStore()
    repo = create_aggregate_repository(SoundscapeAggregate, event_store=store)
    monkeypatch.setattr(store, "read_stream", _connection_refused)
    agg_id = uuid4()

    with pytest.raises(ConnectionError):
        _run(load_or_create(repo, agg_id, SoundscapeAggregate))
    with pytest.raises(ConnectionError):
        _run(load_if_exists(repo, agg_id))


def test_load_if_exists_returns_none_for_unknown_stream() -> None:
    """A read of an unknown id reports absence, not an error."""
    repo = create_aggregate_repository(SoundscapeAggregate, event_store=InMemoryEventStore())
    assert _run(load_if_exists(repo, uuid4())) is None


def test_tension_read_answers_503_when_store_is_unreachable(
    client: TestClient, owned_session_id: str
) -> None:
    """GET /tension must not answer with the canned default during a store outage."""
    session_id = owned_session_id
    seeded = client.post(
        CALCULATE_URL,
        json={
            "session_id": session_id,
            "combat_active": True,
            "combat_round": 2,
            "enemy_cr_balance": 2.5,
            "lowest_party_health_ratio": 0.4,
        },
    )
    assert seeded.status_code == 200, seeded.text

    with store_outage():
        resp = client.get(f"{TENSION_URL}?session_id={session_id}")
    assert resp.status_code == 503, resp.text
    assert resp.json()["detail"] == "Event store is unavailable"


def test_tension_write_answers_503_and_keeps_stored_history(
    client: TestClient, owned_session_id: str
) -> None:
    """A failed load on POST /tension/calculate writes nothing and answers 503."""
    session_id = owned_session_id
    seeded = client.post(
        CALCULATE_URL,
        json={
            "session_id": session_id,
            "combat_active": True,
            "combat_round": 2,
            "enemy_cr_balance": 2.5,
            "lowest_party_health_ratio": 0.4,
        },
    )
    assert seeded.status_code == 200, seeded.text
    stored_score = seeded.json()["tension_score"]

    with store_outage():
        resp = client.post(
            CALCULATE_URL,
            json={"session_id": session_id, "combat_active": False, "combat_round": 0},
        )
    assert resp.status_code == 503, resp.text

    after = client.get(f"{TENSION_URL}?session_id={session_id}")
    assert after.status_code == 200, after.text
    assert after.json()["tension_score"] == stored_score


def test_load_or_404_raises_404_with_detail_for_unknown_stream() -> None:
    """A missing stream answers 404 with the caller's detail text."""
    repo = create_aggregate_repository(SoundscapeAggregate, event_store=InMemoryEventStore())

    with pytest.raises(HTTPException) as caught:
        _run(load_or_404(repo, uuid4(), "Soundscape not found"))
    assert caught.value.status_code == 404
    assert caught.value.detail == "Soundscape not found"


def test_load_or_404_returns_stored_aggregate() -> None:
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
    _run(repo.save(fresh))

    loaded = _run(load_or_404(repo, agg_id, "unused"))
    assert loaded.state.tension_score == 7


def test_load_or_404_propagates_store_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """A store outage is never a 404."""
    store = InMemoryEventStore()
    repo = create_aggregate_repository(SoundscapeAggregate, event_store=store)
    monkeypatch.setattr(store, "read_stream", _connection_refused)

    with pytest.raises(ConnectionError):
        _run(load_or_404(repo, uuid4(), "unused"))


def test_save_or_conflict_maps_version_conflict_to_the_chosen_error(
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
        _run(
            save_or_conflict(
                repo,
                aggregate,
                lambda: HTTPException(status_code=409, detail="changed"),
            )
        )
    assert caught.value.status_code == 409
    assert caught.value.detail == "changed"


def test_save_or_conflict_saves_without_conflict() -> None:
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

    _run(save_or_conflict(repo, aggregate, lambda: RuntimeError("must not fire")))
    assert _run(load_if_exists(repo, agg_id)) is not None


def test_lazy_repository_builds_once_and_set_replaces_it() -> None:
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


def _run[T](awaitable: Awaitable[T]) -> T:
    return asyncio.run(_as_coroutine(awaitable))


async def _as_coroutine[T](awaitable: Awaitable[T]) -> T:
    return await awaitable
