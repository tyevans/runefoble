"""Blackbox tests: gateway campaign routes proxy to game_session (TASK-0591).

The gateway is called through its public HTTP routes with signed bearer tokens. game_session
runs as a live loopback upstream (tests/helpers/live_services.py). Setup goes through public
routes only (create, invite, join, roles). Governed by ADR-0001, ADR-0007, ADR-0015.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app

from tests.helpers.live_services import closed_port_url, serve, unavailable_app


def _auth(issuer, sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


@pytest.fixture
def client(game_session_upstream: str, character_sheet_upstream: str) -> Iterator[TestClient]:
    """Enter the gateway lifespan after the upstream URL is set, so the proxy sees it."""
    with TestClient(gateway_app) as gateway_client:
        yield gateway_client


def _create(client: TestClient, headers: dict[str, str], title: str = "Shadows") -> dict:
    res = client.post(
        "/api/v1/campaigns", json={"title": title, "setting": "Gothic"}, headers=headers
    )
    assert res.status_code == 201, res.text
    return res.json()


def _invite(client: TestClient, headers: dict[str, str], campaign_id: str, **body: Any) -> str:
    res = client.post(
        f"/api/v1/campaigns/{campaign_id}/invites",
        json={"role": "player", **body},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()["token"]


def test_create_join_and_list_members_through_the_gateway(client, trusted_ws_issuer) -> None:
    owner = _auth(trusted_ws_issuer, "dm-evelyn")
    player = _auth(trusted_ws_issuer, "player-marcus")
    campaign = _create(client, owner)
    assert campaign["role"] == "owner"
    assert campaign["owner_id"] == "dm-evelyn"

    token = _invite(client, owner, campaign["id"])
    joined = client.post("/api/v1/campaigns/join", json={"invite_token": token}, headers=player)
    assert joined.status_code == 200, joined.text
    assert joined.json()["role"] == "player"

    members = client.get(f"/api/v1/campaigns/{campaign['id']}/members", headers=owner).json()
    assert {m["user_id"]: m["role"] for m in members} == {
        "dm-evelyn": "owner",
        "player-marcus": "player",
    }
    listed = client.get("/api/v1/campaigns", headers=player).json()
    assert campaign["id"] in [c["id"] for c in listed]


def test_body_user_id_is_ignored_and_the_token_identity_is_used(client, trusted_ws_issuer) -> None:
    owner = _auth(trusted_ws_issuer, "dm-evelyn")
    res = client.post(
        "/api/v1/campaigns",
        json={"title": "Spoofed", "user_id": "someone-else", "owner_id": "someone-else"},
        headers=owner,
    )
    assert res.status_code == 201
    assert res.json()["owner_id"] == "dm-evelyn"


def test_campaign_listed_after_gateway_app_is_rebuilt(
    game_session_upstream, trusted_ws_issuer
) -> None:
    owner = _auth(trusted_ws_issuer, "dm-evelyn")
    with TestClient(gateway_app) as first:
        campaign = _create(first, owner, title="Survives Restart")

    with TestClient(gateway_app) as rebuilt:
        listed = rebuilt.get("/api/v1/campaigns", headers=owner)
    assert listed.status_code == 200
    assert campaign["id"] in [c["id"] for c in listed.json()]


def test_unreachable_owner_returns_503_on_list(monkeypatch, trusted_ws_issuer) -> None:
    monkeypatch.setenv("RUNEFOBLE_GAME_SESSION_URL", closed_port_url())
    with TestClient(gateway_app) as client:
        res = client.get("/api/v1/campaigns", headers=_auth(trusted_ws_issuer, "dm-evelyn"))
    assert res.status_code == 503
    assert res.json()["upstream"] == "game_session"


def test_owner_server_error_returns_502(monkeypatch, trusted_ws_issuer) -> None:
    with serve(unavailable_app(500)) as url:
        monkeypatch.setenv("RUNEFOBLE_GAME_SESSION_URL", url)
        with TestClient(gateway_app) as client:
            res = client.get("/api/v1/campaigns", headers=_auth(trusted_ws_issuer, "dm-evelyn"))
    assert res.status_code == 502


def test_unknown_campaign_returns_404_from_the_owner(client, trusted_ws_issuer) -> None:
    res = client.get(
        "/api/v1/campaigns/00000000-0000-0000-0000-000000000000",
        headers=_auth(trusted_ws_issuer, "dm-evelyn"),
    )
    assert res.status_code == 404
    assert res.json()["detail"]["error"] == "campaign_not_found"


def test_stranger_is_refused_with_the_owner_permission_body(client, trusted_ws_issuer) -> None:
    campaign = _create(client, _auth(trusted_ws_issuer, "dm-evelyn"))
    res = client.get(
        f"/api/v1/campaigns/{campaign['id']}", headers=_auth(trusted_ws_issuer, "stranger-bob")
    )
    assert res.status_code == 403
    assert res.json()["detail"]["error"] == "permission_denied"


def test_missing_token_is_refused_at_the_gateway(client) -> None:
    assert client.get("/api/v1/campaigns").status_code == 401


def test_patch_requires_manage_and_applies_for_the_owner(client, trusted_ws_issuer) -> None:
    owner = _auth(trusted_ws_issuer, "dm-evelyn")
    player = _auth(trusted_ws_issuer, "player-marcus")
    campaign = _create(client, owner, title="Original")
    token = _invite(client, owner, campaign["id"])
    client.post("/api/v1/campaigns/join", json={"invite_token": token}, headers=player)

    denied = client.patch(
        f"/api/v1/campaigns/{campaign['id']}", json={"title": "Hacked"}, headers=player
    )
    assert denied.status_code == 403

    updated = client.patch(
        f"/api/v1/campaigns/{campaign['id']}", json={"title": "Refined"}, headers=owner
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Refined"


def test_single_use_invite_rejects_the_second_join_with_410(client, trusted_ws_issuer) -> None:
    owner = _auth(trusted_ws_issuer, "dm-evelyn")
    campaign = _create(client, owner)
    token = _invite(client, owner, campaign["id"], max_uses=1)
    first = client.post(
        "/api/v1/campaigns/join",
        json={"invite_token": token},
        headers=_auth(trusted_ws_issuer, "player-a"),
    )
    second = client.post(
        "/api/v1/campaigns/join",
        json={"invite_token": token},
        headers=_auth(trusted_ws_issuer, "player-b"),
    )
    assert first.status_code == 200
    assert second.status_code == 410
    assert second.json()["detail"]["error"] == "invite_exhausted"


def test_owner_grants_dungeon_master_and_dm_can_run_sessions(client, trusted_ws_issuer) -> None:
    owner = _auth(trusted_ws_issuer, "dm-evelyn")
    dm = _auth(trusted_ws_issuer, "dm-kyra")
    campaign = _create(client, owner)
    cid = campaign["id"]

    grant = client.post(
        f"/api/v1/campaigns/{cid}/roles",
        json={"user_id": "dm-kyra", "role": "dungeon_master"},
        headers=owner,
    )
    assert grant.status_code == 200, grant.text
    assert grant.json()["zanzibar_relation"] == f"campaign:{cid}#dungeon_master@user:dm-kyra"

    session = client.post(
        f"/api/v1/campaigns/{cid}/sessions", json={"title": "Night One"}, headers=dm
    )
    assert session.status_code == 201, session.text


def test_role_grant_refuses_non_managers_and_the_owner_role(client, trusted_ws_issuer) -> None:
    owner = _auth(trusted_ws_issuer, "dm-evelyn")
    campaign = _create(client, owner)
    cid = campaign["id"]
    body = {"user_id": "player-marcus", "role": "player"}

    stranger = client.post(
        f"/api/v1/campaigns/{cid}/roles",
        json=body,
        headers=_auth(trusted_ws_issuer, "stranger-bob"),
    )
    assert stranger.status_code == 403

    owner_role = client.post(
        f"/api/v1/campaigns/{cid}/roles",
        json={"user_id": "player-marcus", "role": "owner"},
        headers=owner,
    )
    assert owner_role.status_code == 422


def test_capabilities_reflect_the_callers_grants(client, trusted_ws_issuer) -> None:
    owner = _auth(trusted_ws_issuer, "dm-evelyn")
    campaign = _create(client, owner)
    cid = campaign["id"]

    own = client.get(f"/api/v1/campaigns/{cid}/capabilities", headers=owner).json()
    assert own == {"manage": True, "run_session": True, "play": True, "view": True}

    outsider = client.get(
        f"/api/v1/campaigns/{cid}/capabilities", headers=_auth(trusted_ws_issuer, "stranger-bob")
    ).json()
    assert outsider == {"manage": False, "run_session": False, "play": False, "view": False}


def test_sessions_list_includes_the_seeded_lobby(client, trusted_ws_issuer) -> None:
    owner = _auth(trusted_ws_issuer, "dm-evelyn")
    cid = _create(client, owner)["id"]
    sessions = client.get(f"/api/v1/campaigns/{cid}/sessions", headers=owner)
    assert sessions.status_code == 200
    assert [s["status"] for s in sessions.json()] == ["lobby"]
