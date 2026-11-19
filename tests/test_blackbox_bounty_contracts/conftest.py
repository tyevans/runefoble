"""Shared fixtures and harness for mercenary bounty contracts blackbox tests.

Governed by ADR-0001, ADR-0006, ADR-0007, and Hard Invariant 7.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session.main import app as session_app
from runefoble_auth.spicedb import MockSpiceDBClient

from tests.helpers.ws_identity import SIGNING_ISSUER, bearer

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.fixture
def client(spicedb: MockSpiceDBClient) -> TestClient:
    return TestClient(
        session_app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"}
    )


def create_campaign_session(client: TestClient, owner_id: str) -> tuple[str, str]:
    """Create a campaign as its owner and return (campaign_id, first_session_id)."""
    res = client.post(
        "/api/v1/campaigns",
        json={"title": f"Bounty Campaign {uuid4().hex[:8]}"},
        headers=bearer(owner_id),
    )
    assert res.status_code == 201, res.text
    campaign_id = res.json()["id"]
    sessions = client.get(f"/api/v1/campaigns/{campaign_id}/sessions", headers=bearer(owner_id))
    assert sessions.status_code == 200, sessions.text
    return campaign_id, sessions.json()[0]["id"]


def join_campaign(client: TestClient, campaign_id: str, owner_id: str, member_id: str) -> None:
    """Owner issues a player invite; the member redeems it through the public join route."""
    invite = client.post(
        f"/api/v1/campaigns/{campaign_id}/invites",
        json={"role": "player"},
        headers=bearer(owner_id),
    )
    assert invite.status_code == 201, invite.text
    joined = client.post(
        "/api/v1/campaigns/join",
        json={"invite_token": invite.json()["token"]},
        headers=bearer(member_id),
    )
    assert joined.status_code == 200, joined.text
