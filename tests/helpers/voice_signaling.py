"""Shared setup for voice signaling blackbox tests (TASK-0811).

The `fresh_room_coordinator` fixture gives each test an empty voice room coordinator through
the public seam (`set_voice_room_coordinator`). The helpers read the room only through the
public routes and sockets of `voice_agent`.

Governed by ADR-0001, ADR-0014, and ADR-0015 (c).
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.factory import get_spicedb_client
from voice_agent.coordinator import (
    VoiceRoomCoordinator,
    get_voice_room_coordinator,
    set_voice_room_coordinator,
)

from tests.helpers.module_state import SeamRestorer
from tests.helpers.spicedb_factory import campaign_for
from tests.helpers.voice_identity import voice_auth_headers, voice_ws_subprotocols

ROLE_DM = "dungeon_master"
ROLE_PLAYER = "player"
ROLE_SPECTATOR = "spectator"


@pytest.fixture
def fresh_room_coordinator(default_redis_event_bus, seam_restorer: SeamRestorer) -> Iterator[None]:
    """Replace the voice room coordinator for one test and restore it at teardown."""
    seam_restorer.replace(
        get_voice_room_coordinator,
        set_voice_room_coordinator,
        VoiceRoomCoordinator(event_bus=default_redis_event_bus),
    )
    yield


def grant_spectator(session_id: str, user_id: str) -> None:
    """Write `campaign#spectator` for the user. Spectators hold only the view relation."""
    asyncio.run(
        get_spicedb_client().write_relationship(
            resource_type="campaign",
            resource_id=campaign_for(session_id),
            relation="spectator",
            subject_type="user",
            subject_id=user_id,
        )
    )


def next_frame(ws: Any, frame_type: str) -> dict[str, Any]:
    """Read frames until one has `frame_type`. Earlier frames are skipped."""
    while True:
        frame = ws.receive_json()
        if frame.get("type") == frame_type:
            return frame


def roster(client: TestClient, session_id: str, viewer: str) -> dict[str, dict[str, Any]]:
    """Return the room participants keyed by peer id, as the public room summary lists them."""
    res = client.get(f"/api/v1/voice/rooms/{session_id}", headers=voice_auth_headers(viewer))
    assert res.status_code == 200, res.text
    return {p["peer_id"]: p for p in res.json()["participants"]}


def voice_socket(client: TestClient, session_id: str, peer_id: str, user_id: str, query: str = ""):
    """Open the voice signaling socket for `user_id` as `peer_id`."""
    return client.websocket_connect(
        f"/ws/voice/{session_id}?peer_id={peer_id}{query}",
        subprotocols=voice_ws_subprotocols(user_id),
    )


__all__ = [
    "ROLE_DM",
    "ROLE_PLAYER",
    "ROLE_SPECTATOR",
    "fresh_room_coordinator",
    "grant_spectator",
    "next_frame",
    "roster",
    "voice_socket",
]
