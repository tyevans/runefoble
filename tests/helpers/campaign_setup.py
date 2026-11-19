"""Set up campaigns, sessions and party members through the public game_session routes.

Blackbox tests call these helpers to reach a known state before they assert behaviour.
Every step is a public HTTP call with a signed bearer token. No helper writes SpiceDB,
the event store or any repository.

Governed by ADR-0001, ADR-0014 and Hard Invariant 7.
"""

from __future__ import annotations

from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from tests.helpers.signing_test_issuer import SigningTestIssuer
from tests.helpers.ws_identity import SIGNING_ISSUER, bearer


def create_campaign(
    client: httpx.Client,
    owner_id: str,
    title: str | None = None,
    issuer: SigningTestIssuer = SIGNING_ISSUER,
) -> str:
    """Create a campaign as `owner_id` through `POST /api/v1/campaigns` and return its id."""
    res = client.post(
        "/api/v1/campaigns",
        json={"title": title or f"Campaign {uuid4().hex[:8]}"},
        headers=bearer(owner_id, issuer),
    )
    assert res.status_code == 201, res.text
    return str(res.json()["id"])


def create_campaign_session(client: httpx.Client, owner_id: str) -> tuple[str, str]:
    """Create a campaign as `owner_id` and return (campaign_id, first_session_id).

    The campaign route creates the first session. The session list route returns it.
    """
    campaign_id = create_campaign(client, owner_id)
    sessions = client.get(f"/api/v1/campaigns/{campaign_id}/sessions", headers=bearer(owner_id))
    assert sessions.status_code == 200, sessions.text
    return campaign_id, str(sessions.json()[0]["id"])


def invite_and_join(
    client: httpx.Client,
    campaign_id: str,
    owner_id: str,
    member_id: str,
    role: str = "player",
    issuer: SigningTestIssuer = SIGNING_ISSUER,
) -> None:
    """Owner issues an invite for `role`; `member_id` redeems it through the public join route."""
    invite = client.post(
        f"/api/v1/campaigns/{campaign_id}/invites",
        json={"role": role},
        headers=bearer(owner_id, issuer),
    )
    assert invite.status_code == 201, invite.text
    joined = client.post(
        "/api/v1/campaigns/join",
        json={"invite_token": invite.json()["token"]},
        headers=bearer(member_id, issuer),
    )
    assert joined.status_code == 200, joined.text


def _game_session_client() -> TestClient:
    """Return a client for the game_session app. It shares the test SpiceDB client by factory."""
    from game_session.main import app as session_app

    return TestClient(session_app)


def create_dm_campaign(dm_id: str = "user-test") -> str:
    """Create a campaign that `dm_id` owns through `POST /api/v1/campaigns` and return its id.

    The owner holds `run_session`, so the owner runs the boards of the campaign. Board tests call
    this instead of writing a `dungeon_master` tuple by hand.
    """
    return create_campaign(_game_session_client(), dm_id)


@pytest.fixture
def board_campaign(trusted_ws_issuer) -> str:
    """The campaign that the board test modules share. `user-test` runs it.

    Not autouse. A module that needs it lists it in `pytestmark` or takes it as a parameter.
    """
    return create_dm_campaign("user-test")


@pytest.fixture
def board_campaign_viewer(board_campaign: str) -> None:
    """Join `player-viewer` to the board campaign as a player, through the public invite route."""
    add_member(board_campaign, "user-test", "player-viewer", "player")


def add_member(campaign_id: str, owner_id: str, member_id: str, role: str) -> None:
    """Invite `member_id` as `role` through the public invite and join routes."""
    invite_and_join(_game_session_client(), campaign_id, owner_id, member_id, role)


def create_owned_campaign(client: httpx.Client, title: str = "Owned Campaign") -> str:
    """Create a campaign with the client's own identity and return its id. The caller owns it."""
    res = client.post("/api/v1/campaigns", json={"title": title})
    assert res.status_code == 201, res.text
    return str(res.json()["id"])


async def create_owned_campaign_async(
    client: httpx.AsyncClient, title: str = "Owned Campaign"
) -> str:
    """Async form of `create_owned_campaign` for tests that drive an `AsyncClient`."""
    res = await client.post("/api/v1/campaigns", json={"title": title})
    assert res.status_code == 201, res.text
    return str(res.json()["id"])


def create_owner_session(base_url: str, headers: dict[str, str], campaign_id: str) -> str:
    """Create a session in a campaign through the owner's public `POST .../campaigns/{id}/sessions`."""
    res = httpx.post(
        f"{base_url}/api/v1/campaigns/{campaign_id}/sessions",
        json={"title": "Crypt"},
        headers=headers,
        timeout=5.0,
    )
    assert res.status_code == 201, res.text
    return str(res.json()["id"])
