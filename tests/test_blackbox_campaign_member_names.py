"""Blackbox frontdoor tests: campaign members show verified names (TASK-0887).

The member list shows the edited profile display name first, then the username that the
verified token carried when the member entered the campaign, else null. No name is made
from the user id (ADR-0015). Setup and assertions use only public gateway routes.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app


def _auth(issuer, sub: str, username: str | None) -> dict[str, str]:
    """Bearer headers for `sub`. A None username sends a token with no username claim."""
    if username is None:
        token = issuer.mint(sub, extra_claims={"preferred_username": None})
    else:
        token = issuer.mint(sub, username=username)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client_gw(game_session_upstream, character_sheet_upstream) -> Iterator[TestClient]:
    with TestClient(gateway_app) as gateway_client:
        yield gateway_client


def _create_campaign(client: TestClient, headers: dict[str, str]) -> str:
    res = client.post("/api/v1/campaigns", json={"title": "Named Roster"}, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()["id"]


def _join(client: TestClient, camp_id: str, owner: dict[str, str], joiner: dict[str, str]):
    inv = client.post(
        f"/api/v1/campaigns/{camp_id}/invites", json={"role": "player"}, headers=owner
    )
    assert inv.status_code == 201, inv.text
    res = client.post(
        "/api/v1/campaigns/join", json={"invite_token": inv.json()["token"]}, headers=joiner
    )
    assert res.status_code == 200, res.text


def _names(client: TestClient, camp_id: str, headers: dict[str, str]) -> dict[str, str | None]:
    res = client.get(f"/api/v1/campaigns/{camp_id}/members", headers=headers)
    assert res.status_code == 200, res.text
    return {member["user_id"]: member["username"] for member in res.json()}


def test_members_show_the_verified_usernames(client_gw: TestClient, trusted_ws_issuer):
    owner = _auth(trusted_ws_issuer, "400279375238397981", "evelyn")
    player = _auth(trusted_ws_issuer, "400279375238397982", "marcus")
    camp_id = _create_campaign(client_gw, owner)
    _join(client_gw, camp_id, owner, player)

    assert _names(client_gw, camp_id, owner) == {
        "400279375238397981": "evelyn",
        "400279375238397982": "marcus",
    }


def test_edited_profile_display_name_takes_priority(client_gw: TestClient, trusted_ws_issuer):
    owner = _auth(trusted_ws_issuer, "names-owner-2", "evelyn")
    player = _auth(trusted_ws_issuer, "names-player-2", "marcus")
    camp_id = _create_campaign(client_gw, owner)
    _join(client_gw, camp_id, owner, player)

    patched = client_gw.patch(
        "/api/v1/profile", json={"display_name": "Marcus the Bold"}, headers=player
    )
    assert patched.status_code == 200, patched.text

    assert _names(client_gw, camp_id, owner)["names-player-2"] == "Marcus the Bold"


def test_owner_role_change_keeps_the_member_name(client_gw: TestClient, trusted_ws_issuer):
    owner = _auth(trusted_ws_issuer, "names-owner-3", "evelyn")
    player = _auth(trusted_ws_issuer, "names-player-3", "marcus")
    camp_id = _create_campaign(client_gw, owner)
    _join(client_gw, camp_id, owner, player)

    res = client_gw.post(
        f"/api/v1/campaigns/{camp_id}/roles",
        json={"user_id": "names-player-3", "role": "spectator"},
        headers=owner,
    )
    assert res.status_code == 200, res.text

    assert _names(client_gw, camp_id, owner) == {
        "names-owner-3": "evelyn",
        "names-player-3": "marcus",
    }


def test_token_without_username_records_no_name(client_gw: TestClient, trusted_ws_issuer):
    owner = _auth(trusted_ws_issuer, "names-owner-4", None)
    player = _auth(trusted_ws_issuer, "names-player-4", None)
    camp_id = _create_campaign(client_gw, owner)
    _join(client_gw, camp_id, owner, player)

    assert _names(client_gw, camp_id, owner) == {
        "names-owner-4": None,
        "names-player-4": None,
    }


def test_member_added_by_role_grant_has_no_name(client_gw: TestClient, trusted_ws_issuer):
    owner = _auth(trusted_ws_issuer, "names-owner-5", "evelyn")
    camp_id = _create_campaign(client_gw, owner)

    res = client_gw.post(
        f"/api/v1/campaigns/{camp_id}/roles",
        json={"user_id": "names-granted-5", "role": "player"},
        headers=owner,
    )
    assert res.status_code == 200, res.text

    assert _names(client_gw, camp_id, owner)["names-granted-5"] is None
