"""Blackbox tests for minigame table state on the TavernGame aggregate (TASK-0566).

Governed by Hard Invariant 2 (event-sourced state) and Hard Invariant 7 (frontdoor tests).
Table setup uses only public routes: POST /api/v1/tavern/tables and the table WebSocket.
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session.events import STREAM_TAVERN
from game_session.main import app as session_app
from game_session.minigame_tables.ws_manager import minigame_table_manager
from runefoble_auth.spicedb import MockSpiceDBClient

from tests.helpers.minigame_tables import open_minigame_table
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import SIGNING_ISSUER, ws_subprotocols

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

PATRON = "minigame-tester"


def _auth(user_id: str = PATRON) -> dict[str, str]:
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(user_id)}"}


@pytest.fixture(autouse=True)
def default_table_patron(spicedb: MockSpiceDBClient) -> None:
    asyncio.run(
        spicedb.write_relationship("establishment", "est-default", "patron", "user", PATRON)
    )


@pytest.fixture(autouse=True)
def clean_socket_registry():
    minigame_table_manager.connections.clear()
    yield
    minigame_table_manager.connections.clear()


@pytest.fixture
def session_client():
    with TestClient(session_app, headers=_auth("test-user")) as client:
        yield client


def test_dart_throw_publishes_dart_thrown_on_tavern_stream(
    session_client: TestClient, mock_bus: MockAsyncRedis
) -> None:
    """A dart throw over the socket reaches the tavern stream as a DartThrown event."""
    table_id = f"table-stream-{uuid4().hex[:6]}"
    open_minigame_table(table_id, game_type="darts")

    with session_client.websocket_connect(
        f"/ws/minigames/{table_id}", subprotocols=ws_subprotocols(PATRON)
    ) as ws:
        ws.receive_json()
        ws.send_json({"action": "join", "name": "Kip", "chips": 100})
        ws.receive_json()
        ws.send_json({"action": "throw_dart", "vx": 0.0, "vy": 0.0})
        assert ws.receive_json()["type"] == "dart_thrown"

    event_types = [fields.get("event_type", "") for _, fields in mock_bus.streams[STREAM_TAVERN]]
    assert any("DartThrown" in event_type for event_type in event_types)


def test_socket_connect_does_not_create_an_unopened_table(session_client: TestClient) -> None:
    """Connecting to an id that was never opened fails, and no table appears afterwards."""
    table_id = f"table-never-opened-{uuid4().hex[:6]}"

    with session_client.websocket_connect(
        f"/ws/minigames/{table_id}", subprotocols=ws_subprotocols(PATRON)
    ) as ws:
        msg = ws.receive_json()
        assert msg["type"] == "error" and msg["code"] == "TABLE_NOT_FOUND"

    res = session_client.get(f"/api/v1/tavern/tables/{table_id}", headers=_auth())
    assert res.status_code == 404


def test_action_from_unseated_player_is_rejected_without_state_change(
    session_client: TestClient, mock_bus: MockAsyncRedis
) -> None:
    """A dart from a player who is not seated returns an error and records no event."""
    table_id = f"table-reject-{uuid4().hex[:6]}"
    open_minigame_table(table_id, game_type="darts")

    with session_client.websocket_connect(
        f"/ws/minigames/{table_id}", subprotocols=ws_subprotocols(PATRON)
    ) as ws:
        ws.receive_json()
        ws.send_json({"action": "throw_dart", "vx": 0.0, "vy": 0.0})
        msg = ws.receive_json()
        assert msg["type"] == "error" and msg["code"] == "ACTION_REJECTED"

    assert not any(
        "DartThrown" in fields.get("event_type", "")
        for _, fields in mock_bus.streams.get(STREAM_TAVERN, [])
    )
    res = session_client.get(f"/api/v1/tavern/tables/{table_id}", headers=_auth())
    assert res.status_code == 200 and res.json()["players"] == {}


def test_opening_the_same_table_twice_is_a_conflict(session_client: TestClient) -> None:
    table_id = f"table-dup-{uuid4().hex[:6]}"
    open_minigame_table(table_id, game_type="darts")
    res = session_client.post(
        "/api/v1/tavern/tables",
        json={"table_id": table_id, "establishment_id": "est-default", "game_type": "darts"},
        headers=_auth(),
    )
    assert res.status_code == 409
