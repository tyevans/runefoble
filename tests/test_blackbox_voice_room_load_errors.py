"""Blackbox test: a voice room load failure answers 503 and never replaces the stored room (TASK-0561).

Governed by ADR-0011, ADR-0015 (fail closed) and Hard Invariant 7. The peer joins through the
voice signaling WebSocket, so the room reaches the event store through a public frontdoor. The
store then fails reads. Routes must answer 503. They must not answer 200 with an empty room,
and must not write a new room over the stored one.

`store_outage` routes the process event store reads to an unreachable store.
No application code is mocked.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from voice_agent.coordinator import (
    VoiceRoomCoordinator,
    get_voice_room_coordinator,
    set_voice_room_coordinator,
)
from voice_agent.main import app as voice_app

from tests.helpers.event_store_seam import store_outage
from tests.helpers.module_state import SeamRestorer
from tests.helpers.spicedb_factory import grant_voice_session
from tests.helpers.voice_identity import voice_auth_headers
from tests.helpers.voice_signaling import next_frame, voice_socket

pytestmark = pytest.mark.usefixtures("trusted_voice_issuer")

DM_USER = "user-dm"


@pytest.fixture
def session_id() -> str:
    """Each test owns a room, so the shared process event store holds no leftovers."""
    return f"sess-load-error-{uuid4().hex[:8]}"


@pytest.fixture
def fresh_coordinator(session_id: str, seam_restorer: SeamRestorer) -> Iterator[None]:
    """Replace the process coordinator so its in-memory room cache is empty.

    The DM runs the session campaign, so it holds `session.control` (schema relations only).
    """
    asyncio.run(grant_voice_session(session_id, dm=DM_USER))
    seam_restorer.replace(
        get_voice_room_coordinator, set_voice_room_coordinator, VoiceRoomCoordinator()
    )
    yield


@pytest.fixture
def client() -> TestClient:
    return TestClient(voice_app, headers=voice_auth_headers(DM_USER))


@pytest.fixture
def stored_peer(client: TestClient, session_id: str, fresh_coordinator: None) -> Iterator[None]:
    """Join `peer-stored` through the voice signaling socket. The socket stays open for the test.

    Closing the socket removes the peer from the room, so the socket must outlive the outage.
    """
    with voice_socket(client, session_id, "peer-stored", DM_USER) as ws:
        joined = next_frame(ws, "webrtc_joined")
        assert joined["peer_id"] == "peer-stored"
        yield


def test_room_read_answers_503_and_recovers_the_stored_room(
    client: TestClient,
    session_id: str,
    stored_peer: None,
) -> None:
    """A failed room load answers 503. After recovery the stored peer is still there."""
    with store_outage():
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
    stored_peer: None,
) -> None:
    """A kick on a stored room during a store outage answers 503 and changes nothing."""
    with store_outage():
        resp = client.post(
            f"/api/v1/voice/rooms/{session_id}/kick",
            json={"peer_id": "peer-stored", "reason": "mic_spam"},
        )
    assert resp.status_code == 503, resp.text

    recovered = client.get(f"/api/v1/voice/rooms/{session_id}")
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["participant_count"] == 1
