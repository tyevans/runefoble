"""Shared test harness and fixtures for Rules Compendium UI blackbox tests.

Governed by ADR-0003, ADR-0004, ADR-0013, and Hard Invariant 7.
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from rules_compendium.main import app

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def client() -> Generator[TestClient]:
    """TestClient fixture for rules_compendium FastAPI app."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_homebrew_payload() -> dict[str, Any]:
    """Sample valid homebrew monster entity fixture."""
    return {
        "rule_type": "monster",
        "title": "Abyssal Shadowstalker",
        "content": {
            "challenge_rating": 3.0,
            "creature_type": "fiend",
            "armor_class": 16,
            "hit_points": 45,
            "xp": 700,
            "role": "skirmisher",
            "description": "A stealthy fiend summoned from the Shadowfell.",
        },
    }
