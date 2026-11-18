"""Blackbox tests: campaign responses carry SpiceDB permission flags (TASK-0644).

The App Shell reads `permissions` from the public campaign list and detail routes instead of
comparing role names. Setup goes through public routes only (create, invite, join). Governed by
ADR-0001, ADR-0007, and Hard Invariant 1.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app

_FLAGS = {"view", "manage", "invite", "launch_session", "assign_roles"}


def _auth(issuer, sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


@pytest.fixture
def client(game_session_upstream: str, character_sheet_upstream: str) -> Iterator[TestClient]:
    with TestClient(gateway_app) as gateway_client:
        yield gateway_client


def _create_with_player(client: TestClient, issuer) -> tuple[dict[str, Any], dict, dict]:
    owner = _auth(issuer, "dm-evelyn")
    player = _auth(issuer, "player-marcus")
    campaign = client.post(
        "/api/v1/campaigns", json={"title": "Shadows", "setting": "Gothic"}, headers=owner
    )
    assert campaign.status_code == 201, campaign.text
    cid = campaign.json()["id"]
    invite = client.post(f"/api/v1/campaigns/{cid}/invites", json={"role": "player"}, headers=owner)
    assert invite.status_code == 201, invite.text
    joined = client.post(
        "/api/v1/campaigns/join", json={"invite_token": invite.json()["token"]}, headers=player
    )
    assert joined.status_code == 200, joined.text
    return campaign.json(), owner, player


def test_detail_permissions_split_dm_from_player(client, trusted_ws_issuer) -> None:
    campaign, owner, player = _create_with_player(client, trusted_ws_issuer)
    cid = campaign["id"]

    dm = client.get(f"/api/v1/campaigns/{cid}", headers=owner)
    assert dm.status_code == 200, dm.text
    assert set(dm.json()["permissions"]) == _FLAGS
    assert all(dm.json()["permissions"].values())

    play = client.get(f"/api/v1/campaigns/{cid}", headers=player)
    assert play.status_code == 200, play.text
    permissions = play.json()["permissions"]
    assert permissions["view"] is True
    assert permissions["manage"] is False
    assert permissions["launch_session"] is False
    assert permissions["invite"] is False
    assert permissions["assign_roles"] is False


def test_list_carries_the_same_flags_per_campaign(client, trusted_ws_issuer) -> None:
    campaign, owner, player = _create_with_player(client, trusted_ws_issuer)
    cid = campaign["id"]

    listed = client.get("/api/v1/campaigns", headers=player)
    assert listed.status_code == 200, listed.text
    entry = next(c for c in listed.json() if c["id"] == cid)
    assert entry["permissions"]["view"] is True
    assert entry["permissions"]["launch_session"] is False

    listed_dm = client.get("/api/v1/campaigns", headers=owner)
    entry_dm = next(c for c in listed_dm.json() if c["id"] == cid)
    assert entry_dm["permissions"]["launch_session"] is True
    assert entry_dm["permissions"]["assign_roles"] is True


def test_player_flags_match_the_routes_that_refuse_them(client, trusted_ws_issuer) -> None:
    campaign, _owner, player = _create_with_player(client, trusted_ws_issuer)
    cid = campaign["id"]

    session = client.post(
        f"/api/v1/campaigns/{cid}/sessions", json={"title": "Night 2"}, headers=player
    )
    assert session.status_code == 403
    invite = client.post(
        f"/api/v1/campaigns/{cid}/invites", json={"role": "player"}, headers=player
    )
    assert invite.status_code == 403
