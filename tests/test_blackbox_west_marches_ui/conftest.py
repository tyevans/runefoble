"""Shared fixtures and harness for West Marches UI blackbox test suite (TASK-0176).

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0008: Property and Mutation Testing with Hypothesis
- Hard Invariant 1: SpiceDB Zanzibar object authorization
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from campaign_lore.dependencies import (
    set_spicedb_client,
    set_west_marches_repo,
)
from campaign_lore.main import app as lore_app
from campaign_lore.west_marches_aggregate import WestMarchesAtlasAggregate
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.event_sourcing import create_aggregate_repository

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def spicedb_client() -> MockSpiceDBClient:
    mock_spicedb = MockSpiceDBClient()
    set_spicedb_client(mock_spicedb)
    return mock_spicedb


@pytest.fixture
def client(spicedb_client: MockSpiceDBClient) -> TestClient:
    fresh_repo = create_aggregate_repository(WestMarchesAtlasAggregate)
    set_west_marches_repo(fresh_repo)
    return TestClient(lore_app)


@pytest.fixture
def sample_discovery_payload() -> dict[str, Any]:
    return {
        "name": "Sunken Crypt of Arnor",
        "discovery_type": "dungeon",
        "coordinates": {"x": 280.0, "y": 320.0},
        "discovered_by_party_name": "Party Blue",
        "description": "Flooded ancient crypt guarded by water elementals.",
        "danger_level": 4,
        "metadata": {"entrance": "submerged_tunnel", "biome": "fenland"},
    }
