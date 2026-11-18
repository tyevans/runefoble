"""Frontdoor setup for realtime tests: a campaign with members and a lobby session over HTTP.

The owner creates the campaign. Each member redeems an invite. The owner creates the session.
No SpiceDB relation is written directly (Hard Invariant 7).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator

import httpx
import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app

from tests.helpers.ws_identity import SIGNING_ISSUER


def bearer(sub: str) -> dict[str, str]:
    """Return Bearer headers for a signed token of `sub`."""
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


def open_table(
    gateway: TestClient,
    session_upstream_url: str,
    owner: str,
    members: dict[str, str] | None = None,
) -> tuple[str, str]:
    """Return (campaign_id, session_id). `members` maps user id to invite role."""
    campaign = gateway.post("/api/v1/campaigns", json={"title": "Table"}, headers=bearer(owner))
    assert campaign.status_code == 201, campaign.text
    campaign_id = campaign.json()["id"]
    for user, role in (members or {}).items():
        invite = gateway.post(
            f"/api/v1/campaigns/{campaign_id}/invites", json={"role": role}, headers=bearer(owner)
        )
        assert invite.status_code == 201, invite.text
        joined = gateway.post(
            "/api/v1/campaigns/join",
            json={"invite_token": invite.json()["token"]},
            headers=bearer(user),
        )
        assert joined.status_code == 200, joined.text
    session = httpx.post(
        f"{session_upstream_url}/api/v1/sessions/create",
        json={"campaign_id": campaign_id, "title": "Night", "dm_id": owner},
        headers=bearer(owner),
    )
    assert session.status_code == 200, session.text
    return campaign_id, session.json()["session_id"]


@pytest.fixture
def gateway(game_session_upstream, character_sheet_upstream) -> Iterator[TestClient]:
    """A gateway client wired to live loopback upstreams. Import it into the test module."""
    with TestClient(gateway_app) as client:
        yield client


@pytest.fixture
def table_for(gateway: TestClient, game_session_upstream: str) -> Callable[..., tuple[str, str]]:
    """Return `table_for(owner, members)`, which yields (campaign_id, session_id)."""

    def _open(owner: str, members: dict[str, str] | None = None) -> tuple[str, str]:
        return open_table(gateway, game_session_upstream, owner, members)

    return _open
