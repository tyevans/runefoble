"""Shared fixtures and helper utilities for character leitmotif blackbox tests.

Governed by:
- ADR-0002, ADR-0003, ADR-0006, ADR-0013
- Hard Invariant 1 (SpiceDB Zanzibar), Hard Invariant 6 (File length < 500 lines)
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.mock_spicedb import MockSpiceDBClient
from soundscape.dependencies import reset_dependencies, set_spicedb_client
from soundscape.main import app


@pytest.fixture(autouse=True)
def clean_environment():
    """Ensure clean aggregate, mixer, bus, and authorization state for each test."""
    mock_db = MockSpiceDBClient()
    set_spicedb_client(mock_db)
    reset_dependencies()
    yield
    reset_dependencies()
    mock_db._tuples.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def setup_leitmotif_profile(
    client: TestClient,
    session_id: str,
    character_id: str,
    character_name: str,
    timbre: str,
    tempo: float = 1.0,
    volume: float = 1.0,
) -> None:
    """Register character leitmotif audio signature via public REST frontdoor."""
    client.post(
        "/api/v1/soundscape/leitmotif/profile",
        json={
            "session_id": session_id,
            "character_id": character_id,
            "character_name": character_name,
            "instrument_timbre": timbre,
            "tempo_multiplier": tempo,
            "volume_gain": volume,
        },
    )
