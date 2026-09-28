"""Shared test fixtures for Character Sheet UI blackbox tests.

Governed by ADR-0003, ADR-0004, ADR-0007, ADR-0013, and Hard Invariant 7.
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from character_sheet.main import app as character_app
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def client() -> Generator[TestClient]:
    """TestClient fixture for character_sheet FastAPI app."""
    with TestClient(character_app) as test_client:
        yield test_client


@pytest.fixture
def sample_character_payload() -> dict[str, Any]:
    """Mock character model payload for frontdoor testing."""
    return {
        "name": "Valeros the Bold",
        "character_class": "Fighter / Wizard",
        "max_hp": 40,
        "player_id": "player-marcus",
        "personality_traits": ["Daring", "Loyal"],
    }


@pytest.fixture
def created_character_id(client: TestClient, sample_character_payload: dict[str, Any]) -> str:
    """Fixture providing a freshly created character ID via frontdoor REST."""
    resp = client.post("/api/v1/characters", json=sample_character_payload)
    assert resp.status_code == 200
    return resp.json()["character_id"]
