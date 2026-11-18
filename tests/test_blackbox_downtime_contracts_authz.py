"""Blackbox frontdoor tests for fail-closed authorization in game_session route groups.

Covers tavern, bounties, caravans and West Marches, campfire, and stronghold (TASK-0550).
Setup goes through public routes only: campaign create, invite, and join. No tuple writes.

Governed by ADR-0001, ADR-0014, and Hard Invariant 7.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session.main import app as session_app

from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


def _auth(sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


@pytest.fixture
def client() -> TestClient:
    return TestClient(session_app)


def _campaign_with_session(client: TestClient, owner: str) -> tuple[str, str]:
    res = client.post(
        "/api/v1/campaigns", json={"title": f"Authz {uuid4().hex[:8]}"}, headers=_auth(owner)
    )
    assert res.status_code == 201, res.text
    campaign_id = res.json()["id"]
    sessions = client.get(f"/api/v1/campaigns/{campaign_id}/sessions", headers=_auth(owner))
    assert sessions.status_code == 200, sessions.text
    return campaign_id, sessions.json()[0]["id"]


def _join(client: TestClient, campaign_id: str, owner: str, member: str, role: str) -> None:
    invite = client.post(
        f"/api/v1/campaigns/{campaign_id}/invites", json={"role": role}, headers=_auth(owner)
    )
    assert invite.status_code == 201, invite.text
    joined = client.post(
        "/api/v1/campaigns/join",
        json={"invite_token": invite.json()["token"]},
        headers=_auth(member),
    )
    assert joined.status_code == 200, joined.text


def _bounty_body() -> dict[str, object]:
    return {"title": "Clear the Warren", "target_name": "Goblin Shaman", "escrow_gold": 50}


def test_anonymous_bounty_post_returns_401(client: TestClient) -> None:
    _, session_id = _campaign_with_session(client, "owner_bounty_anon")
    res = client.post(f"/sessions/{session_id}/contracts/bounties", json=_bounty_body())
    assert res.status_code == 401


def test_player_posts_bounty_and_outsider_cannot_complete(client: TestClient) -> None:
    owner, player, outsider = "owner_bounty", "player_bounty", "outsider_bounty"
    campaign_id, session_id = _campaign_with_session(client, owner)
    _join(client, campaign_id, owner, player, "player")

    posted = client.post(
        f"/sessions/{session_id}/contracts/bounties",
        json={**_bounty_body(), "campaign_id": campaign_id},
        headers=_auth(player),
    )
    assert posted.status_code == 201, posted.text
    bounty_id = posted.json()["bounty"]["bounty_id"]

    complete = client.post(
        f"/sessions/{session_id}/contracts/bounties/{bounty_id}/complete",
        json={"proof": "Staff"},
        headers=_auth(outsider),
    )
    assert complete.status_code == 403


def test_shared_world_create_without_token_returns_401(client: TestClient) -> None:
    res = client.post("/api/v1/shared-worlds", json={"name": "Frontier"})
    assert res.status_code == 401


def test_campfire_rest_without_token_returns_401(client: TestClient) -> None:
    _, session_id = _campaign_with_session(client, "owner_campfire_anon")
    res = client.post(f"/api/v1/sessions/{session_id}/rest/campfire", json={})
    assert res.status_code == 401


def test_stronghold_upgrade_by_role(client: TestClient) -> None:
    owner, player, spectator = "owner_stronghold", "player_stronghold", "spectator_stronghold"
    campaign_id, _ = _campaign_with_session(client, owner)
    _join(client, campaign_id, owner, player, "player")
    _join(client, campaign_id, owner, spectator, "spectator")
    url = f"/api/v1/campaigns/{campaign_id}/stronghold/upgrade"
    body = {"facility_id": "watchtower", "gold_spent": 0}
    funded = client.post(
        f"/api/v1/campaigns/{campaign_id}/stronghold/deposit",
        json={"gold": 100, "materials": {"wood": 20}},
        headers=_auth(owner),
    )
    assert funded.status_code == 200, funded.text

    assert client.post(url, json=body).status_code == 401
    assert client.post(url, json=body, headers=_auth(spectator)).status_code == 403
    assert client.post(url, json=body, headers=_auth(player)).status_code == 200


def test_haggling_start_requires_establishment_play(client: TestClient) -> None:
    """A stranger with no campaign grant cannot start haggling in the establishment."""
    owner, stranger = "owner_haggle", "stranger_haggle"
    res = client.post(
        "/api/v1/campaigns", json={"title": f"Haggle {uuid4().hex[:8]}"}, headers=_auth(owner)
    )
    assert res.status_code == 201, res.text
    campaign_id = res.json()["id"]
    settlement = client.post(
        f"/api/v1/campaigns/{campaign_id}/settlements",
        json={"name": "Oakhaven", "scale": "market_town", "districts": ["artisan"]},
        headers=_auth(owner),
    )
    assert settlement.status_code == 201, settlement.text
    establishment = client.post(
        f"/api/v1/settlements/{settlement.json()['settlement_id']}/establishments",
        json={"district_id": "artisan", "category": "commerce", "name": "The Ember Anvil"},
        headers=_auth(owner),
    )
    assert establishment.status_code == 201, establishment.text
    establishment_id = establishment.json()["establishment_id"]
    body = {
        "character_id": "char_stranger",
        "item_id": "helm_iron",
        "base_price": 50,
        "campaign_id": campaign_id,
        "establishment_id": establishment_id,
    }

    denied = client.post("/api/v1/haggling/start", json=body, headers=_auth(stranger))
    assert denied.status_code == 403
    allowed = client.post("/api/v1/haggling/start", json=body, headers=_auth(owner))
    assert allowed.status_code == 200, allowed.text
