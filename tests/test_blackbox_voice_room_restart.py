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
from websockets.sync.client import connect

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
