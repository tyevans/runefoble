"""Blackbox frontdoor tests: the session WebSocket needs `session.participate` for inbound frames.

Governed by TASK-0810, ADR-0001 (`session.participate`, `session.observe`), ADR-0015 (c),
and Hard Invariant 7. Setup runs through public frontdoors only: an owner opens a campaign,
members redeem invites, and the owner opens a session. No relation is written directly.

Observers receive frames. Only participants send them. A refused frame is never relayed.
"""

from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from typing import Any

import pytest
from fastapi.testclient import TestClient
from starlette.testclient import WebSocketTestSession

from tests.helpers.ws_identity import ws_subprotocols
from tests.realtime_session import open_table

SILENCE_SECONDS = 1.0
DICE = {"type": "dice_rolled", "roller_name": "Pip", "total": 17}


@pytest.fixture
def table(gateway: TestClient, game_session_upstream: str) -> Iterator[tuple[str, str]]:
    """A campaign (campaign id, session id) with a DM, a player and a spectator."""
    yield open_table(
        gateway,
        game_session_upstream,
        "dm_quinn",
        {"player_pip": "player", "spectator_sol": "spectator"},
    )


def _frame_within(ws: WebSocketTestSession, seconds: float) -> dict[str, Any] | None:
    """Return the next frame, or None when no frame arrives within `seconds`."""
    pool = ThreadPoolExecutor(max_workers=1)
    pending = pool.submit(ws.receive_json)
    try:
        return pending.result(timeout=seconds)
    except FutureTimeout:
        return None
    finally:
        pool.shutdown(wait=False)


def test_observer_frame_gets_an_error_and_is_not_relayed(gateway, table) -> None:
    _, session_id = table
    path = f"/ws/session/{session_id}"

    with (
        gateway.websocket_connect(path, subprotocols=ws_subprotocols("spectator_sol")) as observer,
        gateway.websocket_connect(path, subprotocols=ws_subprotocols("player_pip")) as player,
    ):
        assert observer.receive_json()["type"] == "connected"
        assert player.receive_json()["type"] == "connected"

        observer.send_json(DICE)
        error = observer.receive_json()

        assert error["type"] == "error"
        assert error["code"] == "PERMISSION_DENIED"
        assert error["action"] == "dice_rolled"
        assert _frame_within(player, SILENCE_SECONDS) is None


def test_participant_frame_reaches_every_socket_of_the_session(gateway, table) -> None:
    _, session_id = table
    path = f"/ws/session/{session_id}"

    with (
        gateway.websocket_connect(path, subprotocols=ws_subprotocols("player_pip")) as player,
        gateway.websocket_connect(path, subprotocols=ws_subprotocols("spectator_sol")) as watcher,
    ):
        assert player.receive_json()["type"] == "connected"
        assert watcher.receive_json()["type"] == "connected"

        player.send_json(DICE)

        assert watcher.receive_json()["total"] == 17
        assert player.receive_json()["total"] == 17


def test_unknown_frame_type_gets_an_error_and_is_not_relayed(gateway, table) -> None:
    _, session_id = table
    path = f"/ws/session/{session_id}"

    with (
        gateway.websocket_connect(path, subprotocols=ws_subprotocols("player_pip")) as player,
        gateway.websocket_connect(path, subprotocols=ws_subprotocols("spectator_sol")) as watcher,
    ):
        assert player.receive_json()["type"] == "connected"
        assert watcher.receive_json()["type"] == "connected"

        player.send_json({"type": "make_me_dm", "total": 99})
        error = player.receive_json()

        assert error["type"] == "error"
        assert error["code"] == "UNKNOWN_FRAME"
        assert _frame_within(watcher, SILENCE_SECONDS) is None


def test_frame_without_a_type_or_action_gets_an_invalid_frame_error(gateway, table) -> None:
    _, session_id = table

    with gateway.websocket_connect(
        f"/ws/session/{session_id}", subprotocols=ws_subprotocols("player_pip")
    ) as player:
        assert player.receive_json()["type"] == "connected"

        player.send_json({"total": 5})
        error = player.receive_json()

        assert error["type"] == "error"
        assert error["code"] == "INVALID_FRAME"


def test_non_json_text_gets_an_invalid_frame_error_and_the_socket_stays_open(
    gateway, table
) -> None:
    _, session_id = table

    with gateway.websocket_connect(
        f"/ws/session/{session_id}", subprotocols=ws_subprotocols("player_pip")
    ) as player:
        assert player.receive_json()["type"] == "connected"

        player.send_text("not json at all")
        assert player.receive_json()["code"] == "INVALID_FRAME"

        player.send_json(DICE)
        assert player.receive_json()["total"] == 17
