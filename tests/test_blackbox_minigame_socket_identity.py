"""Blackbox tests: minigame sockets act as the verified principal only (TASK-0548)."""

import asyncio
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session.main import app as session_app
from runefoble_auth.factory import get_spicedb_client, set_spicedb_client
from runefoble_auth.mock import MockSpiceDBClient

from tests.helpers.minigame_tables import open_minigame_table
from tests.helpers.module_state import SeamRestorer
from tests.helpers.ws_identity import ws_subprotocols

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.fixture
def spicedb(seam_restorer: SeamRestorer):
    mock_db = MockSpiceDBClient()
    seam_restorer.replace(get_spicedb_client, set_spicedb_client, mock_db)
    yield mock_db


def _patron(spicedb: MockSpiceDBClient, establishment: str, user: str) -> None:
    asyncio.run(spicedb.write_relationship("establishment", establishment, "patron", "user", user))


def test_standalone_socket_checks_the_table_establishment(spicedb) -> None:
    """The standalone route has no est-default exemption. The table names its establishment."""
    _patron(spicedb, "est-vip", "vip")
    table_id = f"table-{uuid4().hex[:6]}"
    open_minigame_table(table_id, establishment_id="est-vip", user_id="vip")
    with TestClient(session_app) as client:
        with client.websocket_connect(
            f"/ws/minigames/{table_id}", subprotocols=ws_subprotocols("stranger")
        ) as ws:
            assert ws.receive_json()["code"] == "PERMISSION_DENIED"
        with client.websocket_connect(
            f"/ws/minigames/{table_id}", subprotocols=ws_subprotocols("vip")
        ) as ws:
            assert ws.receive_json()["type"] == "connected"


def test_path_cannot_name_a_different_establishment_than_the_table(spicedb) -> None:
    _patron(spicedb, "est-vip", "vip")
    _patron(spicedb, "est-pub", "vip")
    table_id = f"table-{uuid4().hex[:6]}"
    open_minigame_table(table_id, establishment_id="est-vip", user_id="vip")
    with (
        TestClient(session_app) as client,
        client.websocket_connect(
            f"/ws/establishments/est-pub/tables/{table_id}", subprotocols=ws_subprotocols("vip")
        ) as ws,
    ):
        assert ws.receive_json()["code"] == "TABLE_NOT_FOUND"


def test_forged_player_id_and_roulette_number_are_ignored(spicedb) -> None:
    _patron(spicedb, "est-default", "kip")
    table_id = f"table-{uuid4().hex[:6]}"
    open_minigame_table(table_id, game_type="roulette", user_id="kip")
    with (
        TestClient(session_app) as client,
        client.websocket_connect(
            f"/ws/minigames/{table_id}", subprotocols=ws_subprotocols("kip")
        ) as ws,
    ):
        ws.receive_json()
        ws.send_json({"action": "join", "player_id": "victim", "name": "Kip", "chips": 100})
        assert ws.receive_json()["player_id"] == "kip"
        ws.send_json({"action": "spin_roulette", "winning_number": 500})
        assert 0 <= ws.receive_json()["winning_number"] <= 36
