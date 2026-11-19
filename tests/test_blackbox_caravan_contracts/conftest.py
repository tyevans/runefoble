"""Shared fixtures and harness for caravan contracts blackbox tests.

Governed by: ADR-0001, ADR-0006, ADR-0011, Hard Invariant 7.
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


def create_campaign(client: TestClient, owner_id: str) -> str:
    """Create a campaign as its owner through the public campaign route and return its id."""
    res = client.post(
        "/api/v1/campaigns",
        json={"title": f"Campaign {uuid4().hex[:8]}"},
        headers=bearer(owner_id),
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


def join_campaign(
    client: TestClient, campaign_id: str, owner_id: str, member_id: str, role: str = "player"
) -> None:
    """Owner issues an invite for `role`; the member redeems it through the public join route."""
    invite = client.post(
        f"/api/v1/campaigns/{campaign_id}/invites",
        json={"role": role},
        headers=bearer(owner_id),
    )
    assert invite.status_code == 201, invite.text
    joined = client.post(
        "/api/v1/campaigns/join",
        json={"invite_token": invite.json()["token"]},
        headers=bearer(member_id),
    )
    assert joined.status_code == 200, joined.text
