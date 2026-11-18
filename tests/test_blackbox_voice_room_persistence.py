"""Blackbox test: a voice room survives a coordinator restart (TASK-0702).

Governed by ADR-0011, ADR-0015 (f) and Hard Invariant 2. Every coordinator command saves the
room aggregate before it publishes its event. No in-process cache keeps room state.

Interacts through public frontdoors only:
  - WebSocket `/ws/voice/{session_id}` (peer join)
  - HTTP `GET /api/v1/voice/rooms/{session_id}` (room summary)

The restart is a new coordinator over the same process event store. TASK-0698 moves this
check to a real subprocess restart. The store outage double patches `append` on the process
event store and raises ConnectionError (an OSError, the store error class that services map
to 503). No application code is mocked.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import pytest
import voice_agent.main as va_main
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from gateway_api.signaling import signaling_manager
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.event_sourcing import get_event_store
from voice_agent.room import VoiceRoomCoordinator, set_voice_room_coordinator

from tests.helpers.voice_identity import voice_auth_headers
from tests.helpers.ws_identity import ws_subprotocols

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer", "trusted_voice_issuer")

PEER_USER = "user-persist-peer"


class RecordingEventBus:
    """Records each published event. It replaces the Redis transport at the process boundary."""

    def __init__(self) -> None:
        self.published: list[tuple[str, Any]] = []

    async def publish_event(self, stream: str, event: Any) -> str:
        self.published.append((stream, event))
        return "0-0"


def _store_unreachable(*_args: object, **_kwargs: object) -> None:
    raise ConnectionError("event store unreachable")


@pytest.fixture
def session_id() -> str:
    """Each test owns a room, so the shared process event store holds no leftovers."""
    return f"sess-persist-{uuid4().hex[:8]}"


@pytest.fixture
def spicedb(default_spicedb_client: MockSpiceDBClient) -> MockSpiceDBClient:
    """The strict schema mock that the root conftest installs in every service."""
    return default_spicedb_client


@pytest.fixture(autouse=True)
def reset_coordinator() -> Iterator[None]:
    yield
    set_voice_room_coordinator(None)
    signaling_manager._coordinator = None
    signaling_manager.active_rooms.clear()
    signaling_manager.peer_sessions.clear()


def test_joined_peer_is_still_present_after_a_coordinator_restart(
    session_id: str, spicedb: MockSpiceDBClient, default_redis_event_bus
) -> None:
    """A peer joins through the WebSocket. A new coordinator then reads the room from the store."""
    bus = default_redis_event_bus
    original = VoiceRoomCoordinator(event_bus=bus)
    set_voice_room_coordinator(original)
    signaling_manager._coordinator = original
    asyncio.run(spicedb.write_relationship("campaign", session_id, "player", "user", PEER_USER))

    client = TestClient(gateway_app)
    with client.websocket_connect(
        f"/ws/voice/{session_id}?peer_id=peer-persisted", subprotocols=ws_subprotocols(PEER_USER)
    ) as ws:
        ws.receive_json()
        ws.receive_json()

        restarted = VoiceRoomCoordinator(event_bus=bus)
        set_voice_room_coordinator(restarted)
        signaling_manager._coordinator = restarted

        resp = TestClient(va_main.app, headers=voice_auth_headers(PEER_USER)).get(
            f"/api/v1/voice/rooms/{session_id}"
        )

    assert resp.status_code == 200, resp.text
    assert resp.json()["participant_count"] == 1
    assert resp.json()["participants"][0]["peer_id"] == "peer-persisted"


def test_join_during_store_outage_raises_and_publishes_no_join_event(
    session_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed save stops the command. The join event is not published."""
    bus = RecordingEventBus()
    coordinator = VoiceRoomCoordinator(event_bus=bus)

    with monkeypatch.context() as m:
        m.setattr(get_event_store(), "append", _store_unreachable)
        with pytest.raises(ConnectionError):
            asyncio.run(coordinator.peer_joined(session_id, "peer-lost", PEER_USER, "player"))

    assert bus.published == []
