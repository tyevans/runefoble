"""Blackbox frontdoor tests: a session WebSocket relays only inside its own session.

Governed by TASK-0770, ADR-0001 (`session.observe`), and Hard Invariant 7.

Setup runs through public frontdoors: each owner creates a campaign and a session over HTTP.
Clients connect with the bearer subprotocol. No relation is written directly.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from typing import Any

import pytest
from fastapi.testclient import TestClient
from starlette.testclient import WebSocketTestSession
from starlette.websockets import WebSocketDisconnect

from tests.helpers.ws_identity import ws_subprotocols

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

SILENCE_SECONDS = 1.0


def _receive_within(ws: WebSocketTestSession, seconds: float) -> dict[str, Any] | None:
    """Return the next frame, or None when no frame arrives within `seconds`."""
    pool = ThreadPoolExecutor(max_workers=1)
    pending = pool.submit(ws.receive_json)
    try:
        return pending.result(timeout=seconds)
    except FutureTimeout:
        return None
    finally:
        pool.shutdown(wait=False)


def test_message_reaches_own_session_and_never_another(client_gw: TestClient, open_session) -> None:
    session_a = open_session("dm_alice")
    session_b = open_session("dm_bob")

    with (
        client_gw.websocket_connect(
            f"/ws/session/{session_a}", subprotocols=ws_subprotocols("dm_alice")
        ) as ws_a,
        client_gw.websocket_connect(
            f"/ws/session/{session_b}", subprotocols=ws_subprotocols("dm_bob")
        ) as ws_b,
    ):
        assert ws_a.receive_json()["session_id"] == session_a
        assert ws_b.receive_json()["session_id"] == session_b

        ws_a.send_json({"type": "token_moved", "tokenId": "token-secret", "x": 4, "y": 9})

        assert ws_a.receive_json()["tokenId"] == "token-secret"
        assert _receive_within(ws_b, SILENCE_SECONDS) is None


def test_two_clients_of_one_session_still_share_messages(
    client_gw: TestClient, open_session
) -> None:
    session_id = open_session("dm_carol")

    with (
        client_gw.websocket_connect(
            f"/ws/session/{session_id}", subprotocols=ws_subprotocols("dm_carol")
        ) as ws_first,
        client_gw.websocket_connect(
            f"/ws/session/{session_id}", subprotocols=ws_subprotocols("dm_carol")
        ) as ws_second,
    ):
        assert ws_first.receive_json()["type"] == "connected"
        assert ws_second.receive_json()["type"] == "connected"
        ws_first.send_json({"type": "dice_rolled", "total": 17})
        assert ws_second.receive_json()["total"] == 17


def test_user_without_observe_is_refused_with_4403(client_gw: TestClient, open_session) -> None:
    session_id = open_session("dm_dana")

    with (
        pytest.raises(WebSocketDisconnect) as refused,
        client_gw.websocket_connect(
            f"/ws/session/{session_id}", subprotocols=ws_subprotocols("stranger_eve")
        ) as ws,
    ):
        ws.receive_json()

    assert refused.value.code == 4403
