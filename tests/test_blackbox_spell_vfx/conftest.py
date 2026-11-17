"""Shared fixtures for kinetic spell VFX blackbox test suites."""

from pathlib import Path
from typing import Any

import pytest
from board_state.main import app as board_app
from fastapi.testclient import TestClient
from gateway_api.main import set_event_bus
from runefoble_platform.mock_redis import MockAsyncRedis
from runefoble_platform.redis_bus import RedisStreamsEventBus

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def reset_test_state():
    set_event_bus(None)
    yield
    set_event_bus(None)


@pytest.fixture
def mock_bus() -> MockAsyncRedis:
    bus_client = MockAsyncRedis()
    bus = RedisStreamsEventBus(client=bus_client)
    set_event_bus(bus)
    yield bus_client
    set_event_bus(None)


@pytest.fixture
def client() -> TestClient:
    return TestClient(board_app)


@pytest.fixture
def ui_src() -> Path:
    return REPO_ROOT / "services/board_state/ui/src"


@pytest.fixture
def fireball_payload() -> dict[str, Any]:
    return {
        "spell_name": "Fireball",
        "spell_archetype": "evocation",
        "radius_ft": 20,
        "damage_dice": "8d6",
        "damage_type": "fire",
    }
