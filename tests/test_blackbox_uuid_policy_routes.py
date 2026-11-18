"""Blackbox tests: a malformed UUID path id is refused before any write (TASK-0816).

Each route below used to fall back to a random aggregate id, or to a default value, for a
bad id. Now the route answers 400, names the field, and publishes nothing. The routes
parse the id before the permission check, so a bad id answers 400 for every caller.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session.main import app as session_app

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

BAD_ID = "not-a-uuid"


@pytest.fixture
def client() -> TestClient:
    return TestClient(
        session_app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('policy-user')}"}
    )


@pytest.mark.parametrize(
    ("method", "path", "body", "field"),
    [
        (
            "post",
            f"/api/v1/shared-worlds/{BAD_ID}/caravans/contracts",
            {
                "origin_outpost": "a",
                "destination_outpost": "b",
                "cargo": {"grain": 1},
                "cargo_value": 10,
                "posted_by_campaign_id": str(uuid4()),
                "route_risk_level": "low",
                "reward_gold": 5,
            },
            "shared_world_id",
        ),
        (
            "post",
            f"/api/v1/shared-worlds/{BAD_ID}/discoveries",
            {
                "name": "Ruins",
                "discovery_type": "dungeon",
                "coordinates": {"x": 1.0, "y": 2.0},
                "discovered_by_campaign_id": str(uuid4()),
                "discovered_by_party_name": "The Wayfarers",
            },
            "shared_world_id",
        ),
        (
            "post",
            f"/api/v1/campaigns/{BAD_ID}/stronghold/deposit",
            {"gold": 5},
            "campaign_id",
        ),
    ],
)
def test_malformed_id_is_refused_before_any_write(
    client: TestClient,
    mock_bus: MockAsyncRedis,
    method: str,
    path: str,
    body: dict,
    field: str,
):
    """A bad id returns 400 with the field name. No stream receives an event."""
    resp = getattr(client, method)(path, json=body)

    assert resp.status_code == 400, resp.text
    assert field in resp.text
    assert not mock_bus.streams
