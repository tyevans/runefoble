"""Live SpiceDB frontdoor tests for TASK-0811: voice signaling roles come from the live schema.

The voice routes run against a real SpiceDB container with `runefoble.zed` loaded. The DM
role, the player role, and the refusal of a stranger are decided by the live server. Run with
`make test-authz-live` (needs Docker).

Governed by:
- ADR-0001: SpiceDB Zanzibar Object Authorization
- ADR-0015 (c) and (d): roles come from relations in the schema, never from client values
"""

from __future__ import annotations

import asyncio
import uuid

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from voice_agent.main import app as voice_app

from tests.helpers.spicedb_factory import grant_voice_session, shared_spicedb_client
from tests.helpers.voice_signaling import (
    ROLE_DM,
    ROLE_PLAYER,
    next_frame,
    roster,
    voice_socket,
)

pytestmark = [
    pytest.mark.authz_live,
    pytest.mark.usefixtures("trusted_voice_issuer", "fresh_room_coordinator"),
]

DM = "user-live-dm"
PLAYER = "user-live-player"
STRANGER = "user-live-stranger"
WS_AUTHORIZATION_REFUSED = 4403


@pytest.fixture
def live_voice(live_spicedb_with_schema):
    """The voice service shares the live SpiceDB client for the duration of one test."""
    with shared_spicedb_client(live_spicedb_with_schema.client):
        yield TestClient(voice_app)


@pytest.fixture
def live_session_id(live_voice) -> str:
    sid = f"sess-live-signal-{uuid.uuid4().hex[:8]}"
    asyncio.run(grant_voice_session(sid, dm=DM, players=[PLAYER]))
    return sid


def test_live_schema_gives_the_dm_and_player_their_roles(live_voice, live_session_id):
    """A client cannot claim the DM role. The live relations decide each peer's role."""
    with (
        voice_socket(live_voice, live_session_id, "peer-live-dm", DM, "&role=player") as dm_ws,
        voice_socket(
            live_voice, live_session_id, "peer-live-player", PLAYER, "&role=dungeon_master"
        ) as player_ws,
    ):
        assert next_frame(dm_ws, "connected")["role"] == ROLE_DM
        assert next_frame(player_ws, "connected")["role"] == ROLE_PLAYER

        room = roster(live_voice, live_session_id, PLAYER)
        assert room["peer-live-dm"]["role"] == ROLE_DM
        assert room["peer-live-player"]["role"] == ROLE_PLAYER


def test_live_schema_refuses_a_stranger(live_voice, live_session_id):
    with (
        pytest.raises(WebSocketDisconnect) as exc,
        voice_socket(live_voice, live_session_id, "peer-live-stranger", STRANGER) as ws,
    ):
        ws.receive_json()

    assert exc.value.code == WS_AUTHORIZATION_REFUSED
