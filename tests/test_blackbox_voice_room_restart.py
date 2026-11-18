"""Blackbox restart test: a voice room survives a coordinator restart (TASK-0702, TASK-0698).

Governed by ADR-0011, ADR-0015 (f) and Hard Invariant 2. Every coordinator command saves the
room aggregate before it publishes its event. No in-process cache keeps room state.

The peer joins through the WebSocket `/ws/voice/{session_id}` in one voice_agent child process.
The child stops. A second child reads `GET /api/v1/voice/rooms/{session_id}` over the same
PostgreSQL event store. The test process never builds a second coordinator.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

import httpx
import pytest
from websockets.exceptions import ConnectionClosed
from websockets.sync.client import ClientConnection, connect

from tests.helpers.restart_stack import RestartStack
from tests.helpers.voice_identity import voice_auth_headers
from tests.helpers.ws_identity import ws_subprotocols

pytestmark = pytest.mark.usefixtures("restart_stack")

# A child that has just started can answer slowly on a loaded machine.
REQUEST_TIMEOUT_SECONDS = 30.0


def _get(url: str, **kwargs: Any) -> httpx.Response:
    return httpx.get(url, timeout=REQUEST_TIMEOUT_SECONDS, **kwargs)


def _post(url: str, **kwargs: Any) -> httpx.Response:
    return httpx.post(url, timeout=REQUEST_TIMEOUT_SECONDS, **kwargs)


VOICE_AGENT_APP = "voice_agent.main:app"
PEER_USER = "user-persist-peer"


def test_joined_peer_is_still_present_after_a_coordinator_restart(
    restart_stack: RestartStack,
) -> None:
    """A peer joins through the WebSocket. A restarted coordinator then reads the room."""
    session_id = f"sess-persist-{uuid4().hex[:8]}"
    campaign_id = str(uuid4())
    restart_stack.grant(
        [
            ("campaign", campaign_id, "player", "user", PEER_USER),
            ("session", session_id, "campaign", "campaign", campaign_id),
        ]
    )

    # The coordinator process crashes while the peer is joined. A crash runs no shutdown code,
    # so the room in the event store is the only record. The socket closes after the crash.
    socket = None
    try:
        with restart_stack.start(VOICE_AGENT_APP, crash=True) as base:
            ws_base = base.replace("http://", "ws://", 1)
            socket = connect(
                f"{ws_base}/ws/voice/{session_id}?peer_id=peer-persisted",
                subprotocols=ws_subprotocols(PEER_USER),
            )
            json.loads(socket.recv())
            json.loads(socket.recv())

        with restart_stack.start(VOICE_AGENT_APP) as base:
            resp = _get(
                f"{base}/api/v1/voice/rooms/{session_id}", headers=voice_auth_headers(PEER_USER)
            )
    finally:
        if socket is not None:
            socket.close()

    assert resp.status_code == 200, resp.text
    assert resp.json()["participant_count"] == 1
    assert resp.json()["participants"][0]["peer_id"] == "peer-persisted"


GRACEFUL_RESTART_CLOSE_CODE = 1012
RESTART_PEER_A = "user-restart-a"
RESTART_PEER_B = "user-restart-b"


def _open_joined_peer(
    base: str, session_id: str, user: str, peer_id: str
) -> tuple[ClientConnection, dict[str, Any]]:
    """Open a voice socket. Return it with the `webrtc_joined` frame that lists the room."""
    ws_base = base.replace("http://", "ws://", 1)
    socket = connect(
        f"{ws_base}/ws/voice/{session_id}?peer_id={peer_id}",
        subprotocols=ws_subprotocols(user),
    )
    while True:
        frame = json.loads(socket.recv(timeout=REQUEST_TIMEOUT_SECONDS))
        if frame.get("type") == "webrtc_joined":
            return socket, frame


def _close_code_after_drain(socket: ClientConnection) -> int | None:
    """Read until the socket closes. Return the close code the server sent."""
    while True:
        try:
            socket.recv(timeout=REQUEST_TIMEOUT_SECONDS)
        except ConnectionClosed as exc:
            return exc.rcvd.code if exc.rcvd is not None else None


def test_joined_peers_keep_their_seats_through_a_graceful_restart(
    restart_stack: RestartStack,
) -> None:
    """SIGTERM closes each peer with 1012 and keeps the room. Peers resume on reconnect."""
    session_id = f"sess-graceful-{uuid4().hex[:8]}"
    campaign_id = str(uuid4())
    restart_stack.grant(
        [
            ("campaign", campaign_id, "player", "user", RESTART_PEER_A),
            ("campaign", campaign_id, "player", "user", RESTART_PEER_B),
            ("session", session_id, "campaign", "campaign", campaign_id),
        ]
    )

    sockets: list[ClientConnection] = []
    # Leaving the block sends SIGTERM. The child shuts down gracefully with sockets open.
    with restart_stack.start(VOICE_AGENT_APP) as base:
        sockets.append(_open_joined_peer(base, session_id, RESTART_PEER_A, "peer-restart-a")[0])
        sockets.append(_open_joined_peer(base, session_id, RESTART_PEER_B, "peer-restart-b")[0])
    try:
        close_codes = [_close_code_after_drain(socket) for socket in sockets]
    finally:
        for socket in sockets:
            socket.close()

    assert close_codes == [GRACEFUL_RESTART_CLOSE_CODE, GRACEFUL_RESTART_CLOSE_CODE]

    with restart_stack.start(VOICE_AGENT_APP) as base:
        resp = _get(
            f"{base}/api/v1/voice/rooms/{session_id}", headers=voice_auth_headers(RESTART_PEER_A)
        )
        assert resp.status_code == 200, resp.text
        assert sorted(p["peer_id"] for p in resp.json()["participants"]) == [
            "peer-restart-a",
            "peer-restart-b",
        ]

        resumed, joined = _open_joined_peer(base, session_id, RESTART_PEER_A, "peer-restart-a")
        resumed.close()
    assert sorted(p["peer_id"] for p in joined["peers"]) == ["peer-restart-a", "peer-restart-b"]
