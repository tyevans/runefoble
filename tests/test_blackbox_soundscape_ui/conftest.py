"""Shared fixtures and harness for Soundscape UI blackbox test suite (TASK-0154).

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0008: Property and Mutation Testing with Hypothesis
- Hard Invariant 1: SpiceDB Zanzibar object authorization
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from gateway_api.auth import set_spicedb_client as set_gw_spicedb_client
from gateway_api.main import app as gateway_app
from gateway_api.main import set_event_bus as set_gw_event_bus
from runefoble_auth.mock_spicedb import MockSpiceDBClient
from runefoble_auth.spicedb import SpiceDBClient
from soundscape.dependencies import (
    reset_dependencies,
    set_spicedb_client,
)
from soundscape.main import app as soundscape_app

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def clean_environment() -> Generator[None]:
    """Ensure clean soundscape and gateway state for each test."""
    mock_db = MockSpiceDBClient()
    set_spicedb_client(mock_db)
    set_gw_spicedb_client(mock_db)
    set_gw_event_bus(None)
    reset_dependencies()
    set_spicedb_client(mock_db)
    yield
    reset_dependencies()
    set_spicedb_client(SpiceDBClient())
    set_gw_spicedb_client(SpiceDBClient())
    set_gw_event_bus(None)


@pytest.fixture
def client() -> TestClient:
    return TestClient(soundscape_app)


@pytest.fixture
def gateway_client() -> TestClient:
    return TestClient(gateway_app)


@pytest.fixture
def sample_stem_volumes() -> dict[str, float]:
    return {
        "melody": 0.95,
        "percussion": 0.60,
        "drone": 0.40,
        "ambient": 0.85,
    }


@pytest.fixture
def sample_foley_cue() -> dict[str, Any]:
    return {
        "session_id": "sess-ui-01",
        "cue_name": "thunder",
        "cue_type": "foley",
        "volume_gain": 1.1,
        "duck_music": True,
    }


@pytest.fixture
def sample_tension_payload() -> dict[str, Any]:
    return {
        "session_id": "sess-ui-01",
        "combat_active": True,
        "combat_round": 2,
        "enemy_cr_balance": 2.5,
        "lowest_party_health_ratio": 0.4,
    }
