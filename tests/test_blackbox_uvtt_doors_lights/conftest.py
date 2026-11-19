"""Pytest fixtures for UVTT doors and dynamic lighting blackbox tests."""

from __future__ import annotations

import pytest
from board_state.main import app as board_app
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app

from tests.helpers.campaign_setup import create_dm_campaign
from tests.helpers.ws_identity import bearer


@pytest.fixture(autouse=True)
def campaigns_trusted(trusted_ws_issuer) -> None:
    """Trust the shared test issuer in game_session, so tests create campaigns through its routes."""


@pytest.fixture
def board_client() -> TestClient:
    return TestClient(board_app, headers=bearer("user-test"))


@pytest.fixture
def gateway_client() -> TestClient:
    return TestClient(gateway_app)


def create_board(client: TestClient, board_id: str) -> None:
    """Create a board through the POST frontdoor. GET and import never create boards."""
    campaign_id = create_dm_campaign("user-test")
    res = client.post("/api/v1/boards", json={"session_id": board_id, "campaign_id": campaign_id})
    assert res.status_code == 200, res.text
