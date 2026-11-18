"""Shared fixtures for cinematic director blackbox tests (TASK-0190)."""

from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from game_session.main import app as game_session_app
from gateway_api.cinematic_director import CameraTarget, clear_cinematic_directors

from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.fixture(autouse=True)
def clean_environment() -> Generator[None]:
    clear_cinematic_directors()
    yield
    clear_cinematic_directors()


@pytest.fixture
def client(board_gateway: TestClient) -> TestClient:
    return board_gateway


@pytest.fixture
def session_client() -> TestClient:
    return TestClient(
        game_session_app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"}
    )


@pytest.fixture
def mock_party_tokens() -> list[dict[str, Any]]:
    t1 = {"id": "tok-1", "name": "Valeros", "x": 3, "y": 4}
    t2 = {"id": "tok-2", "name": "Kyra", "x": 6, "y": 7}
    return [t1, t2]


@pytest.fixture
def camera_coords() -> tuple[CameraTarget, CameraTarget]:
    c1 = CameraTarget(target_x=0.0, target_y=0.0, zoom=1.0)
    c2 = CameraTarget(target_x=10.0, target_y=20.0, zoom=2.0)
    return c1, c2
