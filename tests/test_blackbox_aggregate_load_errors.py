"""Blackbox tests: aggregate load errors surface as 503, never as empty aggregates (TASK-0561).

Governed by ADR-0011 (eventsource-py), ADR-0015 (fail closed) and Hard Invariant 7.
Only "aggregate not found" may create a new aggregate. A store outage must not create a
stream with an existing aggregate id, and must not return canned data.

The store double wraps the process event store and raises a connection error on reads. It
sits at the store boundary. The code under test is not mocked.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Iterator
from uuid import uuid4

import pytest
from eventsource.adapters.memory.store import InMemoryEventStore
from fastapi.testclient import TestClient
from runefoble_platform.aggregate_loading import load_if_exists, load_or_create
from runefoble_platform.event_sourcing import create_aggregate_repository, get_event_store
from soundscape.aggregate import SoundscapeAggregate
from soundscape.dependencies import reset_dependencies
from soundscape.main import app

from tests.helpers.ws_identity import SIGNING_ISSUER

TENSION_URL = "/api/v1/soundscape/tension"
CALCULATE_URL = "/api/v1/soundscape/tension/calculate"


def _auth_headers(sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


def _connection_refused(*_args: object, **_kwargs: object) -> None:
    raise ConnectionError("event store unreachable")


@pytest.fixture(autouse=True)
def clean_soundscape_environment() -> Iterator[None]:
    reset_dependencies()
    yield
    reset_dependencies()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, headers=_auth_headers("soundscape-tester"))


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
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """GET /tension must not answer with the canned default during a store outage."""
    session_id = "session-outage-read"
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

    with monkeypatch.context() as m:
        m.setattr(get_event_store(), "read_stream", _connection_refused)
        resp = client.get(f"{TENSION_URL}?session_id={session_id}")
    assert resp.status_code == 503, resp.text
    assert resp.json()["detail"] == "Event store is unavailable"


def test_tension_write_answers_503_and_keeps_stored_history(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed load on POST /tension/calculate writes nothing and answers 503."""
    session_id = "session-outage-write"
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

    with monkeypatch.context() as m:
        m.setattr(get_event_store(), "read_stream", _connection_refused)
        resp = client.post(
            CALCULATE_URL,
            json={"session_id": session_id, "combat_active": False, "combat_round": 0},
        )
    assert resp.status_code == 503, resp.text

    after = client.get(f"{TENSION_URL}?session_id={session_id}")
    assert after.status_code == 200, after.text
    assert after.json()["tension_score"] == stored_score


def _run[T](awaitable: Awaitable[T]) -> T:
    return asyncio.run(_as_coroutine(awaitable))


async def _as_coroutine[T](awaitable: Awaitable[T]) -> T:
    return await awaitable
