"""Blackbox tests: aggregate load errors surface as 503, never as empty aggregates (TASK-0561).

Governed by ADR-0011 (eventsource-py), ADR-0015 (fail closed) and Hard Invariant 7.
A store outage must not create a stream with an existing aggregate id, and must not return
canned data. The helper-level cases run in tests/test_aggregate_loading.py.

The store double wraps the process event store and raises a connection error on reads. It
sits at the store boundary. The code under test is not mocked.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from soundscape.main import app

from tests.helpers.event_store_seam import store_outage
from tests.helpers.ws_identity import bearer

TENSION_URL = "/api/v1/soundscape/tension"
CALCULATE_URL = "/api/v1/soundscape/tension/calculate"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, headers=bearer("soundscape-tester"))


@pytest.fixture
def owned_session_id(trusted_ws_issuer, game_session_upstream) -> str:
    """Create a campaign and a session through the gateway frontdoor. The test subject owns both."""
    headers = bearer("soundscape-tester")
    with TestClient(gateway_app) as gateway:
        campaign = gateway.post(
            "/api/v1/campaigns",
            json={"title": "Outage Vault", "setting": "Underdark"},
            headers=headers,
        )
        assert campaign.status_code == 201, campaign.text
        session = gateway.post(
            f"/api/v1/campaigns/{campaign.json()['id']}/sessions",
            json={"title": "Store Outage"},
            headers=headers,
        )
        assert session.status_code == 201, session.text
        return session.json()["id"]


def test_tension_read_answers_503_when_store_is_unreachable(
    client: TestClient, owned_session_id: str
) -> None:
    """GET /tension must not answer with the canned default during a store outage."""
    session_id = owned_session_id
    seeded = client.post(
        CALCULATE_URL,
        json={
            "session_id": session_id,
            "combat_active": True,
            "combat_round": 2,
            "enemy_cr_balance": 2.5,
            "lowest_party_health_ratio": 0.4,
        },
    )
    assert seeded.status_code == 200, seeded.text

    with store_outage():
        resp = client.get(f"{TENSION_URL}?session_id={session_id}")
    assert resp.status_code == 503, resp.text
    assert resp.json()["detail"] == "Event store is unavailable"


def test_tension_write_answers_503_and_keeps_stored_history(
    client: TestClient, owned_session_id: str
) -> None:
    """A failed load on POST /tension/calculate writes nothing and answers 503."""
    session_id = owned_session_id
    seeded = client.post(
        CALCULATE_URL,
        json={
            "session_id": session_id,
            "combat_active": True,
            "combat_round": 2,
            "enemy_cr_balance": 2.5,
            "lowest_party_health_ratio": 0.4,
        },
    )
    assert seeded.status_code == 200, seeded.text
    stored_score = seeded.json()["tension_score"]

    with store_outage():
        resp = client.post(
            CALCULATE_URL,
            json={"session_id": session_id, "combat_active": False, "combat_round": 0},
        )
    assert resp.status_code == 503, resp.text

    after = client.get(f"{TENSION_URL}?session_id={session_id}")
    assert after.status_code == 200, after.text
    assert after.json()["tension_score"] == stored_score
