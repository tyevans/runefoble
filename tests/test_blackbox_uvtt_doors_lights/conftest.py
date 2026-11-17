"""Pytest fixtures for UVTT doors and dynamic lighting blackbox tests."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest
from board_state.main import app as board_app
from fastapi.testclient import TestClient
from gateway_api.auth import get_spicedb_client
from gateway_api.main import app as gateway_app
from gateway_api.main import set_event_bus
from runefoble_auth.spicedb import MockSpiceDBClient


@pytest.fixture
def board_client() -> TestClient:
    return TestClient(board_app)


@pytest.fixture
def gateway_client() -> TestClient:
    return TestClient(gateway_app)


@pytest.fixture(autouse=True)
def clean_environment():
    """Ensure clean storage, mock spicedb, and event bus for each test."""
    with patch("gateway_api.auth.get_spicedb_client", return_value=MockSpiceDBClient()):
        set_event_bus(None)
        yield
        set_event_bus(None)


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
