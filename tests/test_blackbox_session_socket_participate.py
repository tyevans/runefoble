"""Blackbox frontdoor tests: the session WebSocket needs `session.participate` for inbound frames.

A client never sends a server kind. The gateway refuses `session_started`, `turn_advanced`,
`dice_rolled`, `token_moved` and `dm_whisper` from every sender, the DM included (TASK-0910).

Governed by TASK-0810, TASK-0910, ADR-0001 (`session.participate`, `session.observe`), ADR-0015 (c),
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
ACTION = {"type": "token_action", "action": "cast", "tokenId": "token-pip", "total": 17}
SERVER_KINDS = ("session_started", "turn_advanced", "dice_rolled", "token_moved", "dm_whisper")


@pytest.fixture
def table(gateway: TestClient, game_session_upstream: str) -> Iterator[tuple[str, str]]:
    """A campaign (campaign id, session id) with a DM, a player and a spectator."""
    yield open_table(
        gateway,
        game_session_upstream,
        "dm_quinn",
        {"player_pip": "player", "spectator_sol": "spectator"},
    )


@pytest.mark.parametrize("sender", ["player_pip", "dm_quinn"])
def test_a_server_kind_from_any_client_is_unknown_and_not_relayed(
    gateway, table, sender: str
) -> None:
    campaign_id, session_id = table
    path = f"/ws/session/{session_id}"

    with (
        gateway.websocket_connect(path, subprotocols=ws_subprotocols(sender)) as forger,
        gateway.websocket_connect(path, subprotocols=ws_subprotocols("spectator_sol")) as watcher,
    ):
        assert forger.receive_json()["type"] == "connected"
        assert watcher.receive_json()["type"] == "connected"

        for kind in SERVER_KINDS:
            forger.send_json(
                {
                    "type": kind,
                    "campaignId": campaign_id,
                    "sessionId": session_id,
                    "status": "active",
                    "whisper": {"content": "The DM never wrote this."},
                }
            )
            error = forger.receive_json()
            assert (error["type"], error["code"]) == ("error", "UNKNOWN_FRAME"), kind

        assert _frame_within(watcher, SILENCE_SECONDS) is None


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

        observer.send_json(ACTION)
        error = observer.receive_json()

        assert error["type"] == "error"
        assert error["code"] == "PERMISSION_DENIED"
        assert error["action"] == "token_action"
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

        player.send_json(ACTION)

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

        player.send_json(ACTION)
        assert player.receive_json()["total"] == 17
