"""Blackbox restart test for minigame table state on the TavernGame aggregate (TASK-0566, TASK-0698).

Governed by Hard Invariant 2 (event-sourced state) and Hard Invariant 7 (frontdoor tests).

The table opens, and a bet is placed over the socket, in one child process. The child stops.
A second child reads the table over HTTP. Only the event store survives the restart.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

import httpx
import pytest
from websockets.sync.client import connect

from tests.helpers.restart_stack import RestartStack
from tests.helpers.ws_identity import SIGNING_ISSUER, ws_subprotocols

pytestmark = pytest.mark.usefixtures("restart_stack")

# A child that has just started can answer slowly on a loaded machine.
REQUEST_TIMEOUT_SECONDS = 30.0


def _get(url: str, **kwargs: Any) -> httpx.Response:
    return httpx.get(url, timeout=REQUEST_TIMEOUT_SECONDS, **kwargs)


def _post(url: str, **kwargs: Any) -> httpx.Response:
    return httpx.post(url, timeout=REQUEST_TIMEOUT_SECONDS, **kwargs)


GAME_SESSION_APP = "game_session.main:app"
PATRON = "minigame-tester"


def _auth(user_id: str = PATRON) -> dict[str, str]:
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(user_id)}"}


def _recv(ws) -> dict:
    return json.loads(ws.recv())


def test_table_state_survives_socket_layer_restart(restart_stack: RestartStack) -> None:
    """A bet placed over the socket is still on the table after the service restarts."""
    table_id = f"table-restart-{uuid4().hex[:6]}"
    restart_stack.grant([("establishment", "est-default", "patron", "user", PATRON)])

    with restart_stack.start(GAME_SESSION_APP) as base:
        opened = _post(
            f"{base}/api/v1/tavern/tables",
            json={"table_id": table_id, "establishment_id": "est-default", "game_type": "darts"},
            headers=_auth(),
        )
        assert opened.status_code == 201, opened.text

        ws_base = base.replace("http://", "ws://", 1)
        with connect(
            f"{ws_base}/ws/minigames/{table_id}", subprotocols=ws_subprotocols(PATRON)
        ) as ws:
            assert _recv(ws)["type"] == "connected"
            ws.send(json.dumps({"action": "join", "name": "Kip", "chips": 100}))
            assert _recv(ws)["type"] == "player_joined"
            ws.send(json.dumps({"action": "bet", "amount": 10, "bet_type": "dart_wager"}))
            assert _recv(ws)["type"] == "bet_placed"

    with restart_stack.start(GAME_SESSION_APP) as base:
        res = _get(f"{base}/api/v1/tavern/tables/{table_id}", headers=_auth())

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["pot"] == 10
    assert body["players"][PATRON]["chips"] == 90
