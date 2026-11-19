"""Board socket clients receive each placed token live (TASK-0928).

A token placed through `POST /api/v1/boards/{id}/tokens` is broadcast as one `token_placed`
frame to every open `/ws/boards/{id}` socket. A refused placement sends no frame.

Governed by Hard Invariant 7, ADR-0001, ADR-0014 and ADR-0015. Campaign roles and character
ownership are written on the shared SpiceDB mock, the process boundary. Assertions read HTTP
and WebSocket output only.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from typing import Any
from uuid import uuid4

import pytest
from board_state.main import app
from fastapi.testclient import TestClient

from tests.helpers.ws_identity import bearer, ws_subprotocols

DM = "dm-evelyn"
PLAYER = "player-valeros"
SILENCE_SECONDS = 1.0
FRAME_SECONDS = 5.0


def _write(spicedb, kind: str, rid: str, relation: str, subject_type: str, subject: str) -> None:
    asyncio.run(spicedb.write_relationship(kind, rid, relation, subject_type, subject))


def _frame_within(ws, seconds: float) -> dict[str, Any] | None:
    """Return the next frame, or None when no frame arrives within `seconds`."""
    pool = ThreadPoolExecutor(max_workers=1)
    pending = pool.submit(ws.receive_json)
    try:
        return pending.result(timeout=seconds)
    except FutureTimeout:
        return None
    finally:
        pool.shutdown(wait=False)


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
    session_id = f"t0928-{uuid4().hex}"
    res = client.post(
        "/api/v1/boards",
        json={"session_id": session_id, "campaign_id": campaign_id, "cols": 10, "rows": 10},
        headers=bearer(DM),
    )
    assert res.status_code == 200, res.text
    return session_id, character_id


def test_a_placed_token_reaches_every_open_board_socket(
    client: TestClient, table: tuple[str, str]
) -> None:
    session_id, character_id = table
    path = f"/ws/boards/{session_id}"
    with (
        client.websocket_connect(path, subprotocols=ws_subprotocols(DM)) as dm,
        client.websocket_connect(path, subprotocols=ws_subprotocols(PLAYER)) as player,
    ):
        assert dm.receive_json()["type"] == "connected"
        assert player.receive_json()["type"] == "connected"

        placed = client.post(
            f"/api/v1/boards/{session_id}/tokens",
            json={
                "token_id": "valeros",
                "name": "Valeros",
                "token_type": "pc",
                "x": 2,
                "y": 3,
                "character_id": character_id,
            },
            headers=bearer(PLAYER),
        )
        assert placed.status_code == 200, placed.text

        for ws in (dm, player):
            frame = _frame_within(ws, FRAME_SECONDS)
            assert frame is not None, "no token_placed frame arrived"
            assert frame["type"] == "token_placed"
            assert frame["session_id"] == session_id
            assert frame["token"] == placed.json()
            assert _frame_within(ws, SILENCE_SECONDS) is None


def test_a_refused_placement_sends_no_board_frame(
    client: TestClient, table: tuple[str, str]
) -> None:
    session_id, _ = table
    with client.websocket_connect(
        f"/ws/boards/{session_id}", subprotocols=ws_subprotocols(DM)
    ) as dm:
        assert dm.receive_json()["type"] == "connected"

        refused = client.post(
            f"/api/v1/boards/{session_id}/tokens",
            json={"name": "Boulder", "token_type": "obstacle", "x": 3, "y": 3},
            headers=bearer(PLAYER),
        )

        assert refused.status_code == 403, refused.text
        assert _frame_within(dm, SILENCE_SECONDS) is None
