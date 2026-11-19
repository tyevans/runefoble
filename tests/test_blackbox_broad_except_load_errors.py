"""Blackbox tests: load and authorization failures surface as 503, never as success or 404 (TASK-0699).

Governed by ADR-0001 (fail closed), ADR-0011 (eventsource-py), ADR-0015 and Hard Invariant 7.
A store outage must not answer "not found", must not answer with an empty aggregate, and must
not write over stored history. A SpiceDB outage must answer 503, never a denial or an allow.

The store double patches `read_stream` on the process event store (the store boundary). The
SpiceDB double patches `check_permission` on the shared test client (the SpiceDB boundary).
No application code is mocked.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from uuid import uuid4

import pytest
from campaign_lore.dependencies import set_west_marches_repo
from campaign_lore.main import app as lore_app
from campaign_lore.west_marches_aggregate import WestMarchesAtlasAggregate
from eventsource.adapters.memory.store import InMemoryEventStore
from fastapi.testclient import TestClient
from runefoble_auth.errors import AuthzUnavailableError
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.event_sourcing import (
    create_aggregate_repository,
    get_event_store,
    set_event_store,
)
from runefoble_platform.ws_groups import WebSocketGroups
from soundscape.main import app as soundscape_app
from starlette.websockets import WebSocketDisconnect

from tests.helpers.leitmotif_fixtures import (  # noqa: F401 (registers the fixtures)
    leitmotif_session_id_fixture,
)
from tests.helpers.spicedb_factory import shared_spicedb_client
from tests.helpers.ws_identity import bearer

VISITOR_SUBJECT = "lore-test-visitor"
OUTAGE_DETAIL = "Event store is unavailable"


def _connection_refused(*_args: object, **_kwargs: object) -> None:
    raise ConnectionError("event store unreachable")


async def _spicedb_unreachable(*_args: object, **_kwargs: object) -> bool:
    raise AuthzUnavailableError("SpiceDB did not answer in time")


@pytest.fixture(autouse=True)
def _pin_process_event_store() -> Iterator[None]:
    """Pin an in-memory process store for each test, then drop it.

    Campaign Lore tests run inside a PostgreSQL environment (`lore_backends`). A store read in
    that environment would cache a PostgreSQL store process-wide and leak into later tests.
    """
    set_event_store(InMemoryEventStore())
    yield
    set_event_store(None)


@pytest.fixture
def spicedb_client() -> Iterator[MockSpiceDBClient]:
    mock_db = MockSpiceDBClient()
    with shared_spicedb_client(mock_db):
        yield mock_db


@pytest.fixture
def lore_client(spicedb_client: MockSpiceDBClient, lore_backends) -> Iterator[TestClient]:
    set_west_marches_repo(create_aggregate_repository(WestMarchesAtlasAggregate))
    with TestClient(lore_app, headers=bearer(VISITOR_SUBJECT)) as client:
        yield client


# West Marches atlas: GET overview and POST discovery


def _grant_player(campaign_id: str) -> None:
    asyncio.run(
        get_spicedb_client().write_relationship(
            resource_type="campaign",
            resource_id=campaign_id,
            relation="player",
            subject_type="user",
            subject_id=VISITOR_SUBJECT,
        )
    )


def test_west_marches_overview_answers_503_and_keeps_stored_atlas(
    lore_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed atlas load answers 503. It does not answer 200 with an empty atlas."""
    campaign_id = str(uuid4())
    _grant_player(campaign_id)
    seeded = lore_client.post(
        f"/api/v1/campaigns/{campaign_id}/west-marches/discoveries",
        json={"name": "Stored Cave", "coordinates": {"x": 1.0, "y": 2.0}},
    )
    assert seeded.status_code == 201, seeded.text

    with monkeypatch.context() as m:
        m.setattr(get_event_store(), "read_stream", _connection_refused)
        resp = lore_client.get(f"/api/v1/campaigns/{campaign_id}/west-marches")
    assert resp.status_code == 503, resp.text
    assert resp.json()["detail"] == OUTAGE_DETAIL

    after = lore_client.get(f"/api/v1/campaigns/{campaign_id}/west-marches")
    assert after.status_code == 200, after.text
    assert [d["name"] for d in after.json()["discoveries"]] == ["Stored Cave"]


def test_west_marches_discovery_write_answers_503_and_saves_nothing(
    lore_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed atlas load on POST discoveries writes no discovery and answers 503."""
    campaign_id = str(uuid4())
    _grant_player(campaign_id)

    with monkeypatch.context() as m:
        m.setattr(get_event_store(), "read_stream", _connection_refused)
        resp = lore_client.post(
            f"/api/v1/campaigns/{campaign_id}/west-marches/discoveries",
            json={"name": "Lost Cave", "coordinates": {"x": 3.0, "y": 4.0}},
        )
    assert resp.status_code == 503, resp.text

    after = lore_client.get(f"/api/v1/campaigns/{campaign_id}/west-marches")
    assert after.status_code == 200, after.text
    assert after.json()["discoveries"] == []


# Diegetic handouts and 3D relics: a load error is not a missing handout or relic


def test_handout_read_answers_503_on_store_outage(
    lore_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """GET handout answers 404 only when the stream is absent. A store outage answers 503."""
    handout_id = uuid4()
    with monkeypatch.context() as m:
        m.setattr(get_event_store(), "read_stream", _connection_refused)
        resp = lore_client.get(f"/api/v1/lore/handouts/{handout_id}")
    assert resp.status_code == 503, resp.text


def test_handout_seal_break_answers_503_on_store_outage(
    lore_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """POST break-seal answers 503 on a store outage, not 404."""
    with monkeypatch.context() as m:
        m.setattr(get_event_store(), "read_stream", _connection_refused)
        resp = lore_client.post(
            f"/api/v1/lore/handouts/{uuid4()}/break-seal",
            json={},
        )
    assert resp.status_code == 503, resp.text


def test_relic_read_answers_503_on_store_outage(
    lore_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """GET relic answers 404 only when the stream is absent. A store outage answers 503."""
    with monkeypatch.context() as m:
        m.setattr(get_event_store(), "read_stream", _connection_refused)
        resp = lore_client.get(f"/api/v1/lore/relics/{uuid4()}")
    assert resp.status_code == 503, resp.text


def test_relic_absent_stream_still_answers_404(lore_client: TestClient) -> None:
    """An unknown relic id is still a documented 404. Only the outage path changed."""
    resp = lore_client.get(f"/api/v1/lore/relics/{uuid4()}")
    assert resp.status_code == 404, resp.text


# Leitmotif: SpiceDB outage on the character edit check


@pytest.fixture
def soundscape_client() -> TestClient:
    return TestClient(soundscape_app, headers=bearer("soundscape-tester"))


def test_leitmotif_profile_answers_503_when_spicedb_is_unreachable(
    soundscape_client: TestClient,
    leitmotif_session_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A SpiceDB outage on the edit check answers 503. It is not a denial and not an allow."""
    monkeypatch.setattr(get_spicedb_client(), "check_permission", _spicedb_unreachable)
    resp = soundscape_client.post(
        "/api/v1/soundscape/leitmotif/profile",
        json={
            "session_id": leitmotif_session_id,
            "character_id": "char-outage",
            "character_name": "Outage",
            "instrument_timbre": "lute",
            "tempo_multiplier": 1.0,
            "volume_gain": 1.0,
            "attack_ms": 120,
            "release_ms": 300,
            "duration_ms": 4000,
        },
    )
    assert resp.status_code == 503, resp.text
    assert resp.json()["error"] == "authorization_unavailable"


# Socket groups: a failing socket is pruned, and the other sockets still receive the broadcast


class _Socket:
    """A WebSocket double at the socket boundary. It counts sends and raises on send."""

    def __init__(self, error: BaseException | None = None) -> None:
        self.error = error
        self.attempts = 0
        self.sent: list[dict] = []

    async def send_json(self, message: dict) -> None:
        self.attempts += 1
        if self.error is not None:
            raise self.error
        self.sent.append(message)


def test_broadcast_prunes_a_closed_socket_and_delivers_to_the_rest() -> None:
    groups = WebSocketGroups[str]()
    closed = _Socket(WebSocketDisconnect(code=1006))
    live = _Socket()
    groups.register("table-a", closed)
    groups.register("table-a", live)

    asyncio.run(groups.broadcast("table-a", {"type": "turn"}))
    asyncio.run(groups.broadcast("table-a", {"type": "turn"}))

    assert live.sent == [{"type": "turn"}, {"type": "turn"}]
    assert closed.attempts == 1


def test_broadcast_prunes_a_failing_socket_and_delivers_to_the_rest() -> None:
    groups = WebSocketGroups[str]()
    broken = _Socket(RuntimeError("transport fault"))
    live = _Socket()
    groups.register("table-b", broken)
    groups.register("table-b", live)

    asyncio.run(groups.broadcast("table-b", {"type": "turn"}))
    asyncio.run(groups.broadcast("table-b", {"type": "turn"}))

    assert live.sent == [{"type": "turn"}, {"type": "turn"}]
    assert broken.attempts == 1
