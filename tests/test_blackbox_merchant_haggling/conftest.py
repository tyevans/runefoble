"""Shared fixtures and configuration for merchant haggling blackbox tests.

Governed by ADR-0001, ADR-0002, ADR-0003, ADR-0006, and Hard Invariant 7.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from game_session.main import app
from runefoble_auth.mock import MockSpiceDBClient

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import SIGNING_ISSUER

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.fixture
def client(spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis) -> TestClient:
    return TestClient(app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"})


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
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(dm_id)}"},
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
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(dm_id)}"},
    )
    return est.json()["establishment_id"]
