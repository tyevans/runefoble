"""Shared fixtures for kinetic spell VFX blackbox test suites."""

from pathlib import Path
from typing import Any

import pytest
from board_state.main import app as board_app
from fastapi.testclient import TestClient

from tests.helpers.ws_identity import SIGNING_ISSUER


def bearer(sub: str) -> dict[str, str]:
    """Return the Authorization header for a token that the shared test issuer signs for `sub`."""
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def reset_test_state():
    yield


@pytest.fixture
def client() -> TestClient:
    return TestClient(board_app, headers=bearer("user-test"))


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
