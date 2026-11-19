"""Blackbox tests: duplex playback state lives in the voice room aggregate (TASK-0577).

Governed by ADR-0011, ADR-0015 (f) and Hard Invariant 2. A playback that starts on one replica
is visible on another replica and after a restart. A failed load answers 503 and saves nothing.

Interacts through public HTTP frontdoors only:
  - `POST /api/v1/voice/duplex/playback/start` (start playback)
  - `GET /api/v1/voice/duplex/status/{session_id}` (playback status)
  - `POST /api/v1/voice/rooms/{session_id}/kick` (room command)

The restart is a new coordinator over the same process event store. `store_outage` makes the
store reads fail (load failure) and records each `append` (save spy). No application code is
mocked.
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

pytestmark = pytest.mark.usefixtures("trusted_voice_issuer")

DM_USER = "user-dm-state"
PLAYER_USER = "user-player-state"


@pytest.fixture
def session_id() -> str:
    """Each test owns a session, so the shared process event store holds no leftovers."""
    return f"sess-duplex-state-{uuid4().hex[:8]}"


@pytest.fixture(autouse=True)
def reset_coordinator(seam_restorer: SeamRestorer) -> Iterator[None]:
    seam_restorer.keep(get_voice_room_coordinator, set_voice_room_coordinator)
    yield


@pytest.fixture
def granted_session(session_id: str) -> str:
    asyncio.run(grant_voice_session(session_id, dm=DM_USER, players=[PLAYER_USER]))
    return session_id


def test_playback_started_before_a_restart_is_still_reported_after_it(granted_session: str):
    """A playback that starts through HTTP is still active after a coordinator restart."""
    player = TestClient(voice_app, headers=voice_auth_headers(PLAYER_USER))
    set_voice_room_coordinator(VoiceRoomCoordinator())

    started = player.post(
        "/api/v1/voice/duplex/playback/start",
        json={
            "session_id": granted_session,
            "playback_id": "pb-restart",
            "text": "The bridge groans under the weight of the dragon.",
            "duration_ms": 8000.0,
        },
    )
    assert started.status_code == 200, started.text
    assert player.get(f"/api/v1/voice/duplex/status/{granted_session}").json()["playback_active"]

    set_voice_room_coordinator(VoiceRoomCoordinator())
    status = player.get(f"/api/v1/voice/duplex/status/{granted_session}")

    assert status.status_code == 200, status.text
    assert status.json() == {"session_id": granted_session, "playback_active": True}


def test_playback_start_during_store_outage_answers_503_and_saves_nothing(granted_session: str):
    """A failed room load stops the playback command. No event is saved."""
    player = TestClient(voice_app, headers=voice_auth_headers(PLAYER_USER))

    with store_outage(record_appends=True) as saved:
        resp = player.post(
            "/api/v1/voice/duplex/playback/start",
            json={
                "session_id": granted_session,
                "playback_id": "pb-outage",
                "text": "Hello traveler.",
                "duration_ms": 1000.0,
            },
        )

    assert resp.status_code == 503, resp.text
    assert resp.json()["detail"] == "Event store is unavailable"
    assert saved == []


def test_kick_during_store_outage_answers_503_and_saves_nothing(granted_session: str):
    """A failed room load stops the kick command before any event is saved."""
    dm = TestClient(voice_app, headers=voice_auth_headers(DM_USER))

    with store_outage(record_appends=True) as saved:
        resp = dm.post(
            f"/api/v1/voice/rooms/{granted_session}/kick",
            json={"peer_id": "peer-unknown", "reason": "mic_spam"},
        )

    assert resp.status_code == 503, resp.text
    assert saved == []
