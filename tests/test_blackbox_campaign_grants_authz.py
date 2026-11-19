"""Blackbox frontdoor tests for campaign role grant authorization (TASK-0543).

Governing ADRs: ADR-0001 (SpiceDB Zanzibar), ADR-0007 (campaign membership), ADR-0014 (BDD).
Verifies:
1. Anonymous and non-member callers cannot grant any campaign role, including `owner`.
2. Refused grants write no SpiceDB tuple (checked through public member and session routes).
3. A player cannot grant roles. The owner can grant `dungeon_master`, and the new DM can run sessions.
4. The route rejects `owner` with 422. Ownership moves only with campaign creation.
5. A SpiceDB write failure returns 503 and writes nothing.
"""

import pytest
from fastapi.testclient import TestClient
from gateway_api.auth import get_spicedb_client
from gateway_api.main import app

from tests.helpers.campaign_setup import create_campaign, invite_and_join
from tests.helpers.ws_identity import bearer


@pytest.fixture
def client(game_session_upstream, character_sheet_upstream) -> TestClient:
    """Enter the gateway lifespan after game_session is served, so the proxy reaches it."""
    with TestClient(app) as gateway_client:
        yield gateway_client


def _auth(issuer, sub: str) -> dict[str, str]:
    """Return Bearer headers carrying a token that the gateway verifies for `sub`."""
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


def _member_ids(client, campaign_id: str, owner_headers) -> set[str]:
    """Read the member roster as the owner through the public members route."""
    res = client.get(f"/api/v1/campaigns/{campaign_id}/members", headers=owner_headers)
    assert res.status_code == 200, res.text
    return {m["user_id"] for m in res.json()}


def test_anonymous_role_grant_is_refused_and_writes_nothing(trusted_ws_issuer, client):
    """An anonymous request with role=owner gets 401 and no grant is written."""
    campaign_id = create_campaign(client, "owner_evelyn")
    headers_owner = bearer("owner_evelyn")

    res = client.post(
        f"/api/v1/campaigns/{campaign_id}/roles",
        json={"user_id": "attacker_mallory", "role": "owner"},
    )
    assert res.status_code == 401, res.text

    assert _member_ids(client, campaign_id, headers_owner) == {"owner_evelyn"}


def test_non_member_cannot_grant_a_role_and_no_grant_is_written(client, trusted_ws_issuer):
    """A valid token from a non-member gets 403. No tuple is written."""
    campaign_id = create_campaign(client, "owner_evelyn")
    headers_owner = bearer("owner_evelyn")
    headers_attacker = _auth(trusted_ws_issuer, "attacker_mallory")

    res = client.post(
        f"/api/v1/campaigns/{campaign_id}/roles",
        json={"user_id": "attacker_mallory", "role": "dungeon_master"},
        headers=headers_attacker,
    )
    assert res.status_code == 403, res.text
    assert res.json()["detail"]["error"] == "permission_denied"

    # The owner's roster does not list the attacker.
    assert _member_ids(client, campaign_id, headers_owner) == {"owner_evelyn"}

    # The attacker gained no manage right: a second grant from them is also refused.
    again = client.post(
        f"/api/v1/campaigns/{campaign_id}/roles",
        json={"user_id": "attacker_mallory", "role": "player"},
        headers=headers_attacker,
    )
    assert again.status_code == 403, again.text
    assert _member_ids(client, campaign_id, headers_owner) == {"owner_evelyn"}


def test_player_cannot_grant_roles(trusted_ws_issuer, client):
    """A redeemed player gets 403 when granting a role. The roster does not change."""
    campaign_id = create_campaign(client, "owner_evelyn")
    invite_and_join(client, campaign_id, "owner_evelyn", "player_cadence", "player")
    headers_player = _auth(trusted_ws_issuer, "player_cadence")

    res = client.post(
        f"/api/v1/campaigns/{campaign_id}/roles",
        json={"user_id": "player_cadence", "role": "dungeon_master"},
        headers=headers_player,
    )
    assert res.status_code == 403, res.text

    # The player is still a player: cannot create a session (run_session is required).
    session = client.post(
        f"/api/v1/campaigns/{campaign_id}/sessions",
        json={"title": "Illicit Session", "status": "lobby"},
        headers=headers_player,
    )
    assert session.status_code == 403, session.text


def test_owner_rejects_owner_role_with_422(trusted_ws_issuer, client):
    """Ownership moves only with campaign creation. The route rejects role=owner."""
    campaign_id = create_campaign(client, "owner_evelyn")
    headers_owner = bearer("owner_evelyn")
    invite_and_join(client, campaign_id, "owner_evelyn", "player_cadence", "player")

    res = client.post(
        f"/api/v1/campaigns/{campaign_id}/roles",
        json={"user_id": "player_cadence", "role": "owner"},
        headers=headers_owner,
    )
    assert res.status_code == 422, res.text
    assert _member_ids(client, campaign_id, headers_owner) == {"owner_evelyn", "player_cadence"}


def test_owner_grants_dungeon_master_and_dm_can_run_sessions(trusted_ws_issuer, client):
    """The owner grants dungeon_master. The new DM can then create a session."""
    campaign_id = create_campaign(client, "owner_evelyn")
    headers_owner = bearer("owner_evelyn")
    invite_and_join(client, campaign_id, "owner_evelyn", "dm_arthur", "spectator")
    headers_dm_candidate = _auth(trusted_ws_issuer, "dm_arthur")

    # Before the grant the candidate cannot run a session.
    before = client.post(
        f"/api/v1/campaigns/{campaign_id}/sessions",
        json={"title": "Too Early", "status": "lobby"},
        headers=headers_dm_candidate,
    )
    assert before.status_code == 403, before.text

    grant = client.post(
        f"/api/v1/campaigns/{campaign_id}/roles",
        json={"user_id": "dm_arthur", "role": "dungeon_master"},
        headers=headers_owner,
    )
    assert grant.status_code == 200, grant.text
    assert grant.json()["role"] == "dungeon_master"

    after = client.post(
        f"/api/v1/campaigns/{campaign_id}/sessions",
        json={"title": "Round Table", "status": "lobby"},
        headers=headers_dm_candidate,
    )
    assert after.status_code == 201, after.text


def test_spicedb_write_failure_in_the_owner_surfaces_as_502(trusted_ws_issuer, monkeypatch, client):
    """The owner answers 503 when SpiceDB fails. The gateway maps that upstream 5xx to 502 (TASK-0580)."""
    campaign_id = create_campaign(client, "owner_evelyn")
    headers_owner = bearer("owner_evelyn")
    invite_and_join(client, campaign_id, "owner_evelyn", "dm_arthur", "spectator")

    spicedb = get_spicedb_client()

    async def _unavailable_write(*args, **kwargs):
        raise RuntimeError("SpiceDB unavailable (test double at the process boundary)")

    monkeypatch.setattr(spicedb, "write_relationship", _unavailable_write)

    res = client.post(
        f"/api/v1/campaigns/{campaign_id}/roles",
        json={"user_id": "dm_arthur", "role": "dungeon_master"},
        headers=headers_owner,
    )
    assert res.status_code == 502, res.text
    assert res.json()["upstream"] == "game_session"

    monkeypatch.undo()
    # The DM grant did not land: the candidate still cannot run a session.
    session = client.post(
        f"/api/v1/campaigns/{campaign_id}/sessions",
        json={"title": "Should Fail", "status": "lobby"},
        headers=_auth(trusted_ws_issuer, "dm_arthur"),
    )
    assert session.status_code == 403, session.text


def test_capabilities_reflect_the_callers_grants(trusted_ws_issuer, client):
    """Owner, DM, player, and stranger see the capability flags their grants allow."""
    campaign_id = create_campaign(client, "owner_evelyn")
    headers_owner = bearer("owner_evelyn")
    invite_and_join(client, campaign_id, "owner_evelyn", "player_cadence", "player")
    invite_and_join(client, campaign_id, "owner_evelyn", "dm_arthur", "spectator")
    grant = client.post(
        f"/api/v1/campaigns/{campaign_id}/roles",
        json={"user_id": "dm_arthur", "role": "dungeon_master"},
        headers=headers_owner,
    )
    assert grant.status_code == 200, grant.text

    def _caps(sub: str) -> dict:
        res = client.get(
            f"/api/v1/campaigns/{campaign_id}/capabilities", headers=_auth(trusted_ws_issuer, sub)
        )
        assert res.status_code == 200, res.text
        return res.json()

    assert _caps("owner_evelyn") == {
        "manage": True,
        "run_session": True,
        "play": True,
        "view": True,
    }
    assert _caps("dm_arthur") == {
        "manage": False,
        "run_session": True,
        "play": True,
        "view": True,
    }
    assert _caps("player_cadence") == {
        "manage": False,
        "run_session": False,
        "play": True,
        "view": True,
    }
    assert _caps("attacker_mallory") == {
        "manage": False,
        "run_session": False,
        "play": False,
        "view": False,
    }


def test_capabilities_require_a_verified_token(trusted_ws_issuer, client):
    """Anonymous callers cannot read capability flags."""
    campaign_id = create_campaign(client, "owner_evelyn")
    res = client.get(f"/api/v1/campaigns/{campaign_id}/capabilities")
    assert res.status_code == 401, res.text


def test_capabilities_route_is_in_openapi(client):
    """The capabilities route is published in the gateway OpenAPI document."""
    paths = client.get("/openapi.json").json()["paths"]
    assert "get" in paths["/api/v1/campaigns/{campaign_id}/capabilities"]


def test_removed_public_sync_routes_return_404(trusted_ws_issuer, client):
    """Membership, character-ownership, and token-binding sync routes are gone (TASK-0543)."""
    campaign_id = create_campaign(client, "owner_evelyn")
    headers_owner = bearer("owner_evelyn")
    body = {"campaign_id": campaign_id, "user_id": "attacker_mallory", "role": "owner"}
    for path in (
        "/api/v1/auth/sync/membership",
        "/api/v1/auth/sync/character-ownership",
        "/api/v1/auth/sync/token-binding",
    ):
        res = client.post(path, json=body, headers=headers_owner)
        assert res.status_code == 404, f"{path}: {res.status_code}"
    assert _member_ids(client, campaign_id, headers_owner) == {"owner_evelyn"}
