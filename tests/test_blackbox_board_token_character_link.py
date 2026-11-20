"""The board read names the character of each character token (TASK-0945).

A player client must find the token of its own character to send a typed or spoken move with
the token cell. The board read, the `token_placed` frame and the socket `connected` snapshot
carry `character_id`. A token placed without a character carries `null`.

Governed by Hard Invariant 7, ADR-0001, ADR-0014 and ADR-0015. Campaign roles and character
ownership are written on the shared SpiceDB mock, the process boundary. Assertions read HTTP
and WebSocket output only.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from uuid import uuid4

import pytest
from board_state.main import app
from fastapi.testclient import TestClient

from tests.helpers.ws_identity import bearer, ws_subprotocols

DM = "dm-evelyn"
PLAYER = "player-valeros"


def _write(spicedb, kind: str, rid: str, relation: str, subject_type: str, subject: str) -> None:
    asyncio.run(spicedb.write_relationship(kind, rid, relation, subject_type, subject))


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def table(client: TestClient, spicedb) -> tuple[str, str]:
    """A campaign with a DM and a player, a board, and the player's character. Returns ids."""
    campaign_id = str(uuid4())
    _write(spicedb, "campaign", campaign_id, "dungeon_master", "user", DM)
    _write(spicedb, "campaign", campaign_id, "player", "user", PLAYER)
    character_id = str(uuid4())
    _write(spicedb, "character", character_id, "campaign", "campaign", campaign_id)
    _write(spicedb, "character", character_id, "owner", "user", PLAYER)
    session_id = f"t0945-{uuid4().hex}"
    res = client.post(
        "/api/v1/boards",
        json={"session_id": session_id, "campaign_id": campaign_id, "cols": 10, "rows": 10},
        headers=bearer(DM),
    )
    assert res.status_code == 200, res.text
    return session_id, character_id


def _place(client: TestClient, session_id: str, body: dict, caller: str) -> dict:
    res = client.post(f"/api/v1/boards/{session_id}/tokens", json=body, headers=bearer(caller))
    assert res.status_code == 200, res.text
    return res.json()


def test_the_board_read_names_the_character_of_a_character_token(
    client: TestClient, table: tuple[str, str]
) -> None:
    session_id, character_id = table
    placed = _place(
        client,
        session_id,
        {"name": "Valeros", "token_type": "pc", "x": 2, "y": 3, "character_id": character_id},
        PLAYER,
    )
    assert placed["character_id"] == character_id

    board = client.get(f"/api/v1/boards/{session_id}", headers=bearer(PLAYER))

    assert board.status_code == 200, board.text
    assert board.json()["tokens"][placed["token_id"]]["character_id"] == character_id


def test_a_token_without_a_character_reads_as_null(
    client: TestClient, table: tuple[str, str]
) -> None:
    session_id, _ = table
    placed = _place(
        client, session_id, {"name": "Boulder", "token_type": "obstacle", "x": 4, "y": 4}, DM
    )

    board = client.get(f"/api/v1/boards/{session_id}", headers=bearer(DM))

    assert placed["character_id"] is None
    assert board.json()["tokens"][placed["token_id"]]["character_id"] is None


def test_the_socket_snapshot_names_the_character_of_a_character_token(
    client: TestClient, table: tuple[str, str]
) -> None:
    session_id, character_id = table
    placed = _place(
        client,
        session_id,
        {"name": "Valeros", "token_type": "pc", "x": 1, "y": 1, "character_id": character_id},
        PLAYER,
    )

    with client.websocket_connect(
        f"/ws/boards/{session_id}", subprotocols=ws_subprotocols(PLAYER)
    ) as ws:
        frame = ws.receive_json()

    assert frame["type"] == "connected"
    assert frame["tokens"][placed["token_id"]]["character_id"] == character_id
