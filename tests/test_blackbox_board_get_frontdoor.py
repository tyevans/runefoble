"""Blackbox frontdoor tests for TASK-0617: GET never creates a board or seeds tokens.

Interacts only through public HTTP routes. The store outage case swaps the
event store port for a double that fails on read. No private state is written.
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import board_state.dependencies as board_dependencies
import pytest
from board_state.aggregate import BoardAggregate
from board_state.main import app as board_app
from fastapi.testclient import TestClient
from runefoble_platform.event_sourcing import create_aggregate_repository

from tests.helpers.ws_identity import SIGNING_ISSUER


def bearer(sub: str) -> dict[str, str]:
    """Return the Authorization header for a token that the shared test issuer signs for `sub`."""
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


SEEDED_NAMES = {"Valeros", "Kyra", "Goblin Scout"}


@pytest.fixture
def board_client():
    return TestClient(board_app, headers=bearer("user-test"))


def _new_session_id() -> str:
    return f"task0617-{uuid4().hex}"


def test_get_unknown_board_returns_404(board_client):
    """A GET on an unknown session id returns 404 and does not create a board."""
    session_id = _new_session_id()

    res = board_client.get(f"/api/v1/boards/{session_id}")

    assert res.status_code == 404
    assert SEEDED_NAMES.isdisjoint(res.text.split())


def test_get_unknown_board_stays_unknown(board_client):
    """Repeated GETs on an unknown session id keep returning 404."""
    session_id = _new_session_id()

    first = board_client.get(f"/api/v1/boards/{session_id}")
    second = board_client.get(f"/api/v1/boards/{session_id}")

    assert first.status_code == 404
    assert second.status_code == 404


def test_mutating_unknown_board_returns_404(board_client):
    """Write routes return 404 for unknown sessions. They never create a board."""
    session_id = _new_session_id()

    placed = board_client.post(
        f"/api/v1/boards/{session_id}/tokens",
        json={"name": "Probe", "token_type": "pc", "x": 1, "y": 1},
    )
    assert placed.status_code == 404
    res = board_client.get(f"/api/v1/boards/{session_id}")
    assert res.status_code == 404


def test_post_then_get_returns_only_the_created_board(board_client):
    """POST creates the board. GET returns that board with no extra tokens."""
    session_id = _new_session_id()

    created = board_client.post(
        "/api/v1/boards",
        json={"campaign_id": BOARD_CAMPAIGN, "session_id": session_id, "cols": 6, "rows": 5},
    )
    assert created.status_code == 200

    res = board_client.get(f"/api/v1/boards/{session_id}")

    assert res.status_code == 200
    body = res.json()
    assert body["tokens"] == {}
    assert body["cols"] == 6
    assert body["rows"] == 5
    assert SEEDED_NAMES.isdisjoint(res.text.split())


def test_store_load_failure_propagates_as_server_error_and_keeps_board(board_client):
    """A store failure on load returns 5xx. The stored board is not replaced."""
    session_id = _new_session_id()
    created = board_client.post(
        "/api/v1/boards",
        json={"campaign_id": BOARD_CAMPAIGN, "session_id": session_id, "cols": 4, "rows": 4},
    )
    assert created.status_code == 200
    before = board_client.get(f"/api/v1/boards/{session_id}").json()

    original_repo = board_dependencies.repo
    outage_repo = create_aggregate_repository(
        BoardAggregate, event_store=_OutageStore(original_repo.event_store)
    )
    board_dependencies.repo = outage_repo
    try:
        client = TestClient(board_app, headers=bearer("user-test"), raise_server_exceptions=False)
        res = client.get(f"/api/v1/boards/{session_id}")
    finally:
        board_dependencies.repo = original_repo

    assert 500 <= res.status_code < 600
    after = board_client.get(f"/api/v1/boards/{session_id}")
    assert after.status_code == 200
    assert after.json() == before


class _OutageStore:
    """Event store port double. Every read fails. Writes and other calls pass through."""

    def __init__(self, inner):
        self._inner = inner

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def read_stream(self, *args, **kwargs):
        raise ConnectionError("event store unavailable")


BOARD_CAMPAIGN = "camp-board-fixture"


@pytest.fixture(autouse=True)
def _board_campaign_dm(spicedb):
    """Make `user-test` the DM of the campaign that every board in this module belongs to."""
    asyncio.run(
        spicedb.write_relationship(
            resource_type="campaign",
            resource_id=BOARD_CAMPAIGN,
            relation="dungeon_master",
            subject_type="user",
            subject_id="user-test",
        )
    )
