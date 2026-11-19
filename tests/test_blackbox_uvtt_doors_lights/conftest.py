"""Pytest fixtures for UVTT doors and dynamic lighting blackbox tests."""

from __future__ import annotations

import asyncio

import pytest
from board_state.main import app as board_app
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from runefoble_auth.factory import get_spicedb_client

from tests.helpers.ws_identity import bearer

BOARD_CAMPAIGN = "camp-board-fixture"


@pytest.fixture
def board_client() -> TestClient:
    return TestClient(board_app, headers=bearer("user-test"))


@pytest.fixture
def gateway_client() -> TestClient:
    return TestClient(gateway_app)


def create_board(client: TestClient, board_id: str) -> None:
    """Create a board through the POST frontdoor. GET and import never create boards."""
    grant_permission("campaign", BOARD_CAMPAIGN, "dungeon_master", "user-test")
    res = client.post(
        "/api/v1/boards", json={"session_id": board_id, "campaign_id": BOARD_CAMPAIGN}
    )
    assert res.status_code == 200, res.text


def grant_permission(resource_type: str, resource_id: str, relation: str, subject_id: str) -> None:
    """Grant Zanzibar object permission for blackbox test setup."""
    asyncio.run(
        get_spicedb_client().write_relationship(
            resource_type, resource_id, relation, "user", subject_id
        )
    )
