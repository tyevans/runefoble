"""Blackbox test: a voice room load failure answers 503 and never replaces the stored room (TASK-0561).

Governed by ADR-0011, ADR-0015 (fail closed) and Hard Invariant 7. The room exists in the
event store. The store then fails reads. Routes must answer 503. They must not answer 200 with
an empty room, and must not write a new room over the stored one.

The store double patches `read_stream` on the process event store. It raises ConnectionError.
No application code is mocked.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.event_sourcing import create_aggregate_repository, get_event_store
from voice_agent.coordinator import VoiceRoomCoordinator, set_voice_room_coordinator
from voice_agent.main import app as voice_app
from voice_agent.room_aggregate import VoiceRoomAggregate, to_uuid

from tests.helpers.voice_identity import voice_auth_headers

pytestmark = pytest.mark.usefixtures("trusted_voice_issuer")

DM_USER = "user-dm"


def _connection_refused(*_args: object, **_kwargs: object) -> None:
    raise ConnectionError("event store unreachable")


async def _seed_room_with_one_peer(session_id: str) -> None:
    repo = create_aggregate_repository(VoiceRoomAggregate)
    agg = VoiceRoomAggregate(to_uuid(session_id))
    agg.join_peer(session_id, "peer-stored", DM_USER, "dm", None)
    await repo.save(agg)


@pytest.fixture
def session_id() -> str:
    """Each test owns a room, so the shared process event store holds no leftovers."""
    return f"sess-load-error-{uuid4().hex[:8]}"


@pytest.fixture
def fresh_coordinator(session_id: str) -> Iterator[MockSpiceDBClient]:
    """Replace the process coordinator so its in-memory room cache is empty.

    The DM holds control on the session, as the identity tests seed it.
    """
    spicedb = MockSpiceDBClient()
    asyncio.run(spicedb.write_relationship("session", session_id, "control", "user", DM_USER))
    set_voice_room_coordinator(VoiceRoomCoordinator(spicedb_client=spicedb))
    yield spicedb
    set_voice_room_coordinator(None)


@pytest.fixture
def client() -> TestClient:
    return TestClient(voice_app, headers=voice_auth_headers(DM_USER))


def test_room_read_answers_503_and_recovers_the_stored_room(
    client: TestClient,
    session_id: str,
    fresh_coordinator: MockSpiceDBClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed room load answers 503. After recovery the stored peer is still there."""
    asyncio.run(_seed_room_with_one_peer(session_id))

    with monkeypatch.context() as m:
        m.setattr(get_event_store(), "read_stream", _connection_refused)
        resp = client.get(f"/api/v1/voice/rooms/{session_id}")
    assert resp.status_code == 503, resp.text
    assert resp.json()["detail"] == "Event store is unavailable"

    recovered = client.get(f"/api/v1/voice/rooms/{session_id}")
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["participant_count"] == 1
    assert recovered.json()["participants"][0]["peer_id"] == "peer-stored"


def test_room_kick_answers_503_and_keeps_the_stored_room(
    client: TestClient,
    session_id: str,
    fresh_coordinator: MockSpiceDBClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A kick on a stored room during a store outage answers 503 and changes nothing."""
    asyncio.run(_seed_room_with_one_peer(session_id))

    with monkeypatch.context() as m:
        m.setattr(get_event_store(), "read_stream", _connection_refused)
        resp = client.post(
            f"/api/v1/voice/rooms/{session_id}/kick",
            json={"peer_id": "peer-stored", "reason": "mic_spam"},
        )
    assert resp.status_code == 503, resp.text

    recovered = client.get(f"/api/v1/voice/rooms/{session_id}")
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["participant_count"] == 1
