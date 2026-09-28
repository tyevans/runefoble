"""Shared fixtures and configuration for merchant haggling blackbox tests.

Governed by ADR-0001, ADR-0002, ADR-0003, ADR-0006, and Hard Invariant 7.
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from game_session.dependencies import set_event_bus, set_spicedb_client
from game_session.main import app
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.mock_redis import MockAsyncRedis
from runefoble_platform.redis_bus import RedisStreamsEventBus

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def mock_bus() -> Generator[MockAsyncRedis]:
    bus_client = MockAsyncRedis()
    set_event_bus(RedisStreamsEventBus(client=bus_client))
    yield bus_client
    set_event_bus(None)


@pytest.fixture
def spicedb() -> Generator[MockSpiceDBClient]:
    db = MockSpiceDBClient()
    set_spicedb_client(db)
    yield db
    set_spicedb_client(None)


@pytest.fixture
def client(spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis) -> TestClient:
    return TestClient(app)


def create_test_establishment(client: TestClient, campaign_id: str, dm_id: str) -> str:
    """Create settlement and establishment storefront via frontdoor API."""
    s_res = client.post(
        f"/api/v1/campaigns/{campaign_id}/settlements",
        json={
            "name": "Oakhaven",
            "scale": "market_town",
            "biome": "river_valley",
            "districts": ["artisan"],
        },
        headers={"x-user-id": dm_id},
    )
    settlement_id = s_res.json()["settlement_id"]
    est = client.post(
        f"/api/v1/settlements/{settlement_id}/establishments",
        json={
            "district_id": "artisan",
            "category": "commerce",
            "name": "The Ember Anvil",
            "tier": 2,
            "operating_cost": 20,
        },
        headers={"x-user-id": dm_id},
    )
    return est.json()["establishment_id"]
