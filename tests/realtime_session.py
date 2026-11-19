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

from tests.helpers.campaign_setup import create_campaign, invite_and_join
from tests.helpers.ws_identity import bearer


def open_table(
    gateway: TestClient,
    session_upstream_url: str,
    owner: str,
    members: dict[str, str] | None = None,
) -> tuple[str, str]:
    """Return (campaign_id, session_id). `members` maps user id to invite role."""
    campaign_id = create_campaign(gateway, owner, title="Table")
    for user, role in (members or {}).items():
        invite_and_join(gateway, campaign_id, owner, user, role)
    session = httpx.post(
        f"{session_upstream_url}/api/v1/campaigns/{campaign_id}/sessions",
        json={"title": "Night"},
        headers=bearer(owner),
    )
    assert session.status_code == 201, session.text
    return campaign_id, session.json()["id"]


@pytest.fixture
def gateway(
    game_session_upstream, character_sheet_upstream, voice_agent_upstream
) -> Iterator[TestClient]:
    """A gateway client wired to live loopback upstreams. Import it into the test module."""
    with TestClient(gateway_app) as client:
        yield client


@pytest.fixture
def table_for(gateway: TestClient, game_session_upstream: str) -> Callable[..., tuple[str, str]]:
    """Return `table_for(owner, members)`, which yields (campaign_id, session_id)."""

    def _open(owner: str, members: dict[str, str] | None = None) -> tuple[str, str]:
        return open_table(gateway, game_session_upstream, owner, members)

    return _open
