"""Blackbox frontdoor tests: the session socket group fans out to live peers only (TASK-0820).

Governed by ADR-0015 and Hard Invariant 7. Setup runs through the public frontdoors: a campaign
and session open through HTTP, and each socket joins through the WebSocket route. One socket
closes mid-session. The remaining sockets must still receive every relayed frame.

All sockets open inside one TestClient context, so they share one event loop.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.helpers.ws_identity import ws_subprotocols
from tests.realtime_session import open_table

DICE = {"type": "token_action", "action": "cast", "tokenId": "token-pip", "total": 17}


def test_frame_reaches_every_live_socket_after_a_peer_leaves(
    gateway: TestClient, game_session_upstream: str
) -> None:
    _, session_id = open_table(
        gateway,
        game_session_upstream,
        "dm_quinn",
        {"player_pip": "player", "spectator_sol": "spectator"},
    )
    path = f"/ws/session/{session_id}"

    with gateway.websocket_connect(path, subprotocols=ws_subprotocols("player_pip")) as player:
        assert player.receive_json()["type"] == "connected"

        with gateway.websocket_connect(
            path, subprotocols=ws_subprotocols("spectator_sol")
        ) as watcher:
            assert watcher.receive_json()["type"] == "connected"

            with gateway.websocket_connect(path, subprotocols=ws_subprotocols("dm_quinn")) as dm:
                assert dm.receive_json()["type"] == "connected"

                player.send_json(DICE)
                assert [s.receive_json()["total"] for s in (watcher, dm, player)] == [17, 17, 17]

            # The DM socket has closed and left the group.
            player.send_json(DICE)
            assert watcher.receive_json()["total"] == 17
            assert player.receive_json()["total"] == 17
