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
from gateway_api.campaign_store import campaign_store
from gateway_api.main import app

client = TestClient(app)


def _auth(issuer, sub: str) -> dict[str, str]:
    """Return Bearer headers carrying a token that the gateway verifies for `sub`."""
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


@pytest.fixture(autouse=True)
def reset_store():
    """Reset campaign and session store before each test run."""
    campaign_store.reset()
    yield


def _create_campaign(issuer, owner_sub: str = "owner_evelyn") -> tuple[str, dict[str, str]]:
    """Create a campaign as the owner through the public route. Return its id and owner headers."""
    headers_owner = _auth(issuer, owner_sub)
    res = client.post("/api/v1/campaigns", json={"title": "Grant Test"}, headers=headers_owner)
    assert res.status_code == 201, res.text
    return res.json()["id"], headers_owner


def _join_with_invite(issuer, campaign_id: str, owner_headers, role: str, sub: str) -> None:
    """Create an invite as the owner, then redeem it as `sub` through public routes."""
    inv = client.post(
        f"/api/v1/campaigns/{campaign_id}/invites",
        json={"role": role},
        headers=owner_headers,
    )
    assert inv.status_code == 201, inv.text
    join = client.post(
        "/api/v1/campaigns/join",
        json={"invite_token": inv.json()["token"]},
        headers=_auth(issuer, sub),
    )
    assert join.status_code == 200, join.text


def _member_ids(campaign_id: str, owner_headers) -> set[str]:
    """Read the member roster as the owner through the public members route."""
    res = client.get(f"/api/v1/campaigns/{campaign_id}/members", headers=owner_headers)
    assert res.status_code == 200, res.text
    return {m["user_id"] for m in res.json()}


def test_anonymous_role_grant_is_refused_and_writes_nothing(signing_issuer):
    """An anonymous request with role=owner gets 401 and no grant is written."""
    campaign_id, headers_owner = _create_campaign(signing_issuer)

    res = client.post(
        f"/api/v1/campaigns/{campaign_id}/roles",
        json={"user_id": "attacker_mallory", "role": "owner"},
    )
    assert res.status_code == 401, res.text

    assert _member_ids(campaign_id, headers_owner) == {"owner_evelyn"}


def test_non_member_cannot_grant_owner_and_no_grant_is_written(signing_issuer):
    """A valid token from a non-member gets 403 for role=owner. No tuple is written."""
    campaign_id, headers_owner = _create_campaign(signing_issuer)
    headers_attacker = _auth(signing_issuer, "attacker_mallory")

    res = client.post(
        f"/api/v1/campaigns/{campaign_id}/roles",
        json={"user_id": "attacker_mallory", "role": "owner"},
        headers=headers_attacker,
    )
    assert res.status_code == 403, res.text
    assert res.json()["detail"]["error"] == "permission_denied"

    # Later check: the owner's roster does not list the attacker.
    assert _member_ids(campaign_id, headers_owner) == {"owner_evelyn"}

    # The attacker gained no manage right: the campaign still refuses a role grant from them.
    again = client.post(
        f"/api/v1/campaigns/{campaign_id}/roles",
        json={"user_id": "attacker_mallory", "role": "player"},
        headers=headers_attacker,
    )
    assert again.status_code == 403, again.text
    assert _member_ids(campaign_id, headers_owner) == {"owner_evelyn"}


def test_player_cannot_grant_roles(signing_issuer):
    """A redeemed player gets 403 when granting a role. The roster does not change."""
    campaign_id, headers_owner = _create_campaign(signing_issuer)
    _join_with_invite(signing_issuer, campaign_id, headers_owner, "player", "player_cadence")
    headers_player = _auth(signing_issuer, "player_cadence")

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


def test_owner_rejects_owner_role_with_422(signing_issuer):
    """Ownership moves only with campaign creation. The route rejects role=owner."""
    campaign_id, headers_owner = _create_campaign(signing_issuer)
    _join_with_invite(signing_issuer, campaign_id, headers_owner, "player", "player_cadence")

    res = client.post(
        f"/api/v1/campaigns/{campaign_id}/roles",
        json={"user_id": "player_cadence", "role": "owner"},
        headers=headers_owner,
    )
    assert res.status_code == 422, res.text
    assert _member_ids(campaign_id, headers_owner) == {"owner_evelyn", "player_cadence"}


def test_owner_grants_dungeon_master_and_dm_can_run_sessions(signing_issuer):
    """The owner grants dungeon_master. The new DM can then create a session."""
    campaign_id, headers_owner = _create_campaign(signing_issuer)
    _join_with_invite(signing_issuer, campaign_id, headers_owner, "spectator", "dm_arthur")
    headers_dm_candidate = _auth(signing_issuer, "dm_arthur")

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


def test_spicedb_write_failure_returns_503_and_writes_nothing(signing_issuer, monkeypatch):
    """A failed SpiceDB write returns 503. The grant is not reported as success."""
    campaign_id, headers_owner = _create_campaign(signing_issuer)
    _join_with_invite(signing_issuer, campaign_id, headers_owner, "spectator", "dm_arthur")

    spicedb = get_spicedb_client()

    async def _unavailable_write(*args, **kwargs):
        raise RuntimeError("SpiceDB unavailable (test double at the process boundary)")

    monkeypatch.setattr(spicedb, "write_relationship", _unavailable_write)

    res = client.post(
        f"/api/v1/campaigns/{campaign_id}/roles",
        json={"user_id": "dm_arthur", "role": "dungeon_master"},
        headers=headers_owner,
    )
    assert res.status_code == 503, res.text

    monkeypatch.undo()
    # The DM grant did not land: the candidate still cannot run a session.
    session = client.post(
        f"/api/v1/campaigns/{campaign_id}/sessions",
        json={"title": "Should Fail", "status": "lobby"},
        headers=_auth(signing_issuer, "dm_arthur"),
    )
    assert session.status_code == 403, session.text
