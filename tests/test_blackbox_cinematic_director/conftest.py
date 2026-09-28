"""Shared fixtures for cinematic director blackbox tests (TASK-0190)."""

from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from game_session.main import app as game_session_app
from gateway_api.cinematic_director import CameraTarget, clear_cinematic_directors
from gateway_api.main import app as gateway_app
from gateway_api.spectator import clear_raw_session_state


@pytest.fixture(autouse=True)
def clean_environment() -> Generator[None]:
    clear_cinematic_directors()
    clear_raw_session_state()
    yield
    clear_cinematic_directors()
    clear_raw_session_state()


@pytest.fixture
def client() -> TestClient:
    return TestClient(gateway_app)


@pytest.fixture
def session_client() -> TestClient:
    return TestClient(game_session_app)


@pytest.fixture
def camera_coords() -> tuple[CameraTarget, CameraTarget]:
    c1 = CameraTarget(target_x=0.0, target_y=0.0, zoom=1.0)
    c2 = CameraTarget(target_x=10.0, target_y=20.0, zoom=2.0)
    return c1, c2


@pytest.fixture
def mock_party_tokens() -> list[dict[str, Any]]:
    t1 = {"id": "tok-1", "name": "Valeros", "x": 3, "y": 4}
    t2 = {"id": "tok-2", "name": "Kyra", "x": 6, "y": 7}
    return [t1, t2]


@pytest.fixture
def mock_party_state() -> dict[str, Any]:
    paladin = {"id": "t1", "name": "Sir Roderick", "hp": 52, "max_hp": 60, "dm_notes": "Secret"}
    paladin["conditions"] = ["shield of faith"]
    shadow = {"id": "t2", "name": "Shadow Fiend", "hp": 85, "max_hp": 85, "hidden": True}
    shadow["stat_block"] = {"cr": "5"}
    return {
        "session_id": "sess-san-json",
        "round": 4,
        "tokens": [paladin, shadow],
        "dm_notes": "Secret trap",
        "monster_stat_blocks": {"shadow_fiend": {"ac": 16}},
    }
