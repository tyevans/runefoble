"""Shared fixtures and configuration for merchant haggling blackbox tests.

Governed by ADR-0001, ADR-0002, ADR-0003, ADR-0006, and Hard Invariant 7.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session.main import app
from runefoble_auth.spicedb import MockSpiceDBClient

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


def create_campaign_for(client: TestClient, owner_id: str) -> str:
    """Create a campaign as its owner through the public campaign route and return its id."""
    res = client.post(
        "/api/v1/campaigns",
        json={"title": f"Haggle Campaign {uuid4().hex[:8]}"},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(owner_id)}"},
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


def invite_player(client: TestClient, campaign_id: str, owner_id: str, player_id: str) -> None:
    """Owner issues a player invite; the player redeems it through the public join route."""
    invite = client.post(
        f"/api/v1/campaigns/{campaign_id}/invites",
        json={"role": "player"},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(owner_id)}"},
    )
    assert invite.status_code == 201, invite.text
    joined = client.post(
        "/api/v1/campaigns/join",
        json={"invite_token": invite.json()["token"]},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(player_id)}"},
    )
    assert joined.status_code == 200, joined.text
