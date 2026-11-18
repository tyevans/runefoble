"""Pytest fixtures for UVTT doors and dynamic lighting blackbox tests."""

from __future__ import annotations

import asyncio

import pytest
from board_state.main import app as board_app
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from runefoble_auth.factory import get_spicedb_client

from tests.helpers.ws_identity import SIGNING_ISSUER


def bearer(sub: str) -> dict[str, str]:
    """Return the Authorization header for a token that the shared test issuer signs for `sub`."""
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


@pytest.fixture
def board_client() -> TestClient:
    return TestClient(board_app, headers=bearer("user-test"))


@pytest.fixture
def gateway_client() -> TestClient:
    return TestClient(gateway_app)


def create_board(client: TestClient, board_id: str) -> None:
    """Create a board through the POST frontdoor. GET and import never create boards."""
    res = client.post("/api/v1/boards", json={"session_id": board_id})
    assert res.status_code == 200, res.text


def grant_permission(resource_type: str, resource_id: str, relation: str, subject_id: str) -> None:
    """Grant Zanzibar object permission for blackbox test setup."""
    asyncio.run(
        get_spicedb_client().write_relationship(
            resource_type, resource_id, relation, "user", subject_id
        )
    )
