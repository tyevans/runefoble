"""Shared fixtures for cinematic director blackbox tests (TASK-0190, TASK-0823)."""

import pytest
from fastapi.testclient import TestClient
from game_session.main import app as game_session_app

from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.fixture
def client(board_gateway: TestClient) -> TestClient:
    return board_gateway


@pytest.fixture
def session_client() -> TestClient:
    return TestClient(
        game_session_app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"}
    )
