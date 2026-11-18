"""Blackbox test: a voice room save failure stops the join (TASK-0702).

Governed by ADR-0011, ADR-0015 (f) and Hard Invariant 2. Every coordinator command saves the
room aggregate before it publishes its event. The restart test lives in
test_blackbox_voice_room_restart.py and runs the service as a subprocess.

The store outage double patches `append` on the process event store and raises ConnectionError
(an OSError, the store error class that services map to 503). No application code is mocked.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import pytest
from runefoble_platform.event_sourcing import get_event_store
from voice_agent.room import VoiceRoomCoordinator, set_voice_room_coordinator
from voice_agent.signaling import signaling_manager

pytestmark = pytest.mark.usefixtures("trusted_voice_issuer")

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


@pytest.fixture(autouse=True)
def reset_coordinator() -> Iterator[None]:
    yield
    set_voice_room_coordinator(None)
    signaling_manager._coordinator = None
    signaling_manager.active_rooms.clear()
    signaling_manager.peer_sessions.clear()


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
