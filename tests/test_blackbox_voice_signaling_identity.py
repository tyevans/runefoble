"""Blackbox tests: voice signaling takes identity and role only from the verified principal (TASK-0811).

Governed by ADR-0001, ADR-0015 (c), and Hard Invariant 1. Every socket opens through the public
WebSocket route of `voice_agent`. Session relations are written on the SpiceDB test client,
and the room summary is read through `GET /api/v1/voice/rooms/{session_id}`.
"""

from __future__ import annotations

import asyncio
import uuid

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from voice_agent.main import app as voice_app

from tests.helpers.spicedb_factory import grant_voice_session
from tests.helpers.voice_identity import voice_ws_subprotocols
from tests.helpers.voice_signaling import (
    ROLE_DM,
    ROLE_PLAYER,
    ROLE_SPECTATOR,
    grant_spectator,
    next_frame,
    roster,
    voice_socket,
)

pytestmark = pytest.mark.usefixtures("trusted_voice_issuer", "fresh_room_coordinator")

DM = "user-dm"
PLAYER = "user-player"
SPECTATOR = "user-spectator"
STRANGER = "user-stranger"
WS_AUTHORIZATION_REFUSED = 4403


@pytest.fixture
def session_id() -> str:
    """A fresh session. The DM and the player hold schema relations. The stranger holds none."""
    sid = f"sess-signal-{uuid.uuid4().hex[:8]}"
    asyncio.run(grant_voice_session(sid, dm=DM, players=[PLAYER]))
    return sid


def test_join_frame_cannot_replace_the_verified_user(session_id):
    """A join frame that names another user id leaves the verified user in the roster."""
    with (
        TestClient(voice_app) as client,
        voice_socket(client, session_id, "peer-player", PLAYER) as ws,
    ):
        next_frame(ws, "webrtc_joined")

        ws.send_json({"type": "webrtc_join", "peer_id": "peer-player", "user_id": DM})
        joined = next_frame(ws, "webrtc_joined")

        assert joined["user_id"] == PLAYER
        assert joined["role"] == ROLE_PLAYER
        assert roster(client, session_id, PLAYER)["peer-player"]["user_id"] == PLAYER


def test_join_frame_that_asks_for_another_role_gets_an_error_frame(session_id):
    """A player who asks for the DM role receives an error. The roster keeps the SpiceDB role."""
    with (
        TestClient(voice_app) as client,
        voice_socket(client, session_id, "peer-player", PLAYER) as ws,
    ):
        next_frame(ws, "webrtc_joined")

        ws.send_json({"type": "webrtc_join", "peer_id": "peer-player", "role": ROLE_DM})
        error = next_frame(ws, "error")

        assert error["code"] == "ROLE_MISMATCH"
        assert error["action"] == "webrtc_join"
        assert roster(client, session_id, PLAYER)["peer-player"]["role"] == ROLE_PLAYER


def test_join_frame_that_asks_for_the_verified_role_succeeds(session_id):
    """A join frame that repeats the SpiceDB role is accepted."""
    with (
        TestClient(voice_app) as client,
        voice_socket(client, session_id, "peer-dm", DM) as ws,
    ):
        next_frame(ws, "webrtc_joined")

        ws.send_json({"type": "webrtc_join", "peer_id": "peer-dm", "role": ROLE_DM})
        joined = next_frame(ws, "webrtc_joined")

        assert joined["role"] == ROLE_DM


@pytest.mark.parametrize(
    ("user_id", "claimed_role", "expected_role"),
    [
        (DM, ROLE_PLAYER, ROLE_DM),
        (PLAYER, ROLE_DM, ROLE_PLAYER),
    ],
)
def test_query_role_is_ignored_and_session_relation_sets_the_role(
    session_id, user_id, claimed_role, expected_role
):
    """The role at admission comes from SpiceDB. The `role` query parameter is not an input."""
    with (
        TestClient(voice_app) as client,
        voice_socket(client, session_id, "peer-x", user_id, f"&role={claimed_role}") as ws,
    ):
        connected = next_frame(ws, "connected")

        assert connected["role"] == expected_role
        assert connected["user_id"] == user_id
        assert roster(client, session_id, user_id)["peer-x"]["role"] == expected_role


def test_spectator_role_comes_from_the_view_relation(session_id):
    grant_spectator(session_id, SPECTATOR)

    with (
        TestClient(voice_app) as client,
        voice_socket(client, session_id, "peer-watch", SPECTATOR) as ws,
    ):
        connected = next_frame(ws, "connected")

        assert connected["role"] == ROLE_SPECTATOR


def test_companion_socket_role_comes_from_the_session_relation(session_id):
    """The mobile companion channel reads its role the same way as the signaling room."""
    with (
        TestClient(voice_app) as client,
        client.websocket_connect(
            f"/ws/mobile-companion/{session_id}?peer_id=peer-phone&role={ROLE_DM}",
            subprotocols=voice_ws_subprotocols(PLAYER),
        ) as ws,
    ):
        connected = next_frame(ws, "mobile_companion_connected")

        assert connected["user_id"] == PLAYER
        assert connected["role"] == ROLE_PLAYER


def test_peer_without_session_access_cannot_join(session_id):
    with TestClient(voice_app) as client:
        with (
            pytest.raises(WebSocketDisconnect) as exc,
            voice_socket(client, session_id, "peer-stranger", STRANGER) as ws,
        ):
            ws.receive_json()

        assert exc.value.code == WS_AUTHORIZATION_REFUSED
        assert "peer-stranger" not in roster(client, session_id, PLAYER)


def test_relayed_offer_names_the_sending_socket_as_its_source(session_id):
    """A peer cannot claim another peer's id as the source of an SDP offer."""
    with (
        TestClient(voice_app) as client,
        voice_socket(client, session_id, "peer-player", PLAYER) as ws_player,
        voice_socket(client, session_id, "peer-dm", DM) as ws_dm,
    ):
        next_frame(ws_dm, "webrtc_joined")
        ws_player.send_json(
            {
                "type": "webrtc_offer",
                "from_peer": "peer-dm",
                "to_peer": "peer-dm",
                "sdp": {"type": "offer", "sdp": "v=0"},
            }
        )

        offer = next_frame(ws_dm, "webrtc_offer")

        assert offer["from_peer"] == "peer-player"
