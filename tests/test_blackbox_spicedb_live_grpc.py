"""Blackbox TDD frontdoor test suite for live SpiceDB gRPC integration.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object Authorization
- ADR-0005: Kubernetes-First Infrastructure with Helm and Kind
- ADR-0007: Real-Time Voice and Board Synchronization
- ADR-0009: Continuous Backlog Refinement and Technical Debt Management
- ADR-0015 (a, d): membership comes from invites; no role claim or role route grants access
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup

Membership is created through the public frontdoors (campaign create, invite, join).
Only the live SpiceDB client test writes or deletes tuples directly.
"""

from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session.dependencies import set_spicedb_client as set_session_spicedb
from gateway_api.auth import set_spicedb_client
from gateway_api.main import app
from runefoble_auth.bootstrap_schema import bootstrap_schema
from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient
from runefoble_auth.testing.signing_test_issuer import SigningTestIssuer


@pytest.fixture
def gateway_tc(game_session_upstream) -> Iterator[TestClient]:
    """Gateway client with the lifespan entered after game_session is served."""
    with TestClient(app) as gateway_client:
        yield gateway_client


def _bearer(issuer: SigningTestIssuer, sub: str) -> dict[str, str]:
    """Return Bearer headers carrying a token that the gateway verifies for `sub`."""
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


def _create_campaign_with_session(tc: TestClient, owner_headers: dict[str, str]) -> tuple[str, str]:
    """Create a campaign as the owner and return (campaign_id, first_session_id)."""
    res = tc.post(
        "/api/v1/campaigns",
        json={"title": f"Campaign {uuid4().hex[:8]}"},
        headers=owner_headers,
    )
    assert res.status_code == 201
    campaign_id = res.json()["id"]

    sessions = tc.get(f"/api/v1/campaigns/{campaign_id}/sessions", headers=owner_headers)
    assert sessions.status_code == 200
    return campaign_id, sessions.json()[0]["id"]


def _join_with_invite(
    tc: TestClient,
    campaign_id: str,
    owner_headers: dict[str, str],
    member_headers: dict[str, str],
    role: str = "player",
) -> None:
    """Owner creates an invite for `role`; the member redeems it."""
    invite = tc.post(
        f"/api/v1/campaigns/{campaign_id}/invites",
        json={"role": role},
        headers=owner_headers,
    )
    assert invite.status_code == 201
    joined = tc.post(
        "/api/v1/campaigns/join",
        json={"invite_token": invite.json()["token"]},
        headers=member_headers,
    )
    assert joined.status_code == 200


@pytest.mark.asyncio
async def test_mock_spicedb_frontdoor_role_assignment(trusted_ws_issuer, gateway_tc):
    """Verify invite-based membership and enforcement using MockSpiceDBClient."""
    mock_client = MockSpiceDBClient()
    set_spicedb_client(mock_client)
    set_session_spicedb(mock_client)
    tc = gateway_tc

    owner = _bearer(trusted_ws_issuer, f"owner-{uuid4().hex[:6]}")
    user_alice = _bearer(trusted_ws_issuer, f"user-{uuid4().hex[:6]}")
    camp_id, session_id = _create_campaign_with_session(tc, owner)

    # Not a member -> 403 Forbidden
    res = tc.get(f"/api/v1/sessions/{session_id}", headers=user_alice)
    assert res.status_code == 403
    assert res.json()["detail"]["required_permission"] == "observe"

    # Redeem a player invite
    _join_with_invite(tc, camp_id, owner, user_alice, role="player")

    # Player can view session but cannot advance turn
    res_view = tc.get(f"/api/v1/sessions/{session_id}", headers=user_alice)
    assert res_view.status_code == 200
    assert res_view.json()["id"] == session_id

    res_adv = tc.post(
        f"/api/v1/sessions/{session_id}/turns/advance",
        headers=user_alice,
        json={"next_character_id": "c1"},
    )
    assert res_adv.status_code == 403

    # The owner runs the session as DM and can advance turn
    res_adv_dm = tc.post(
        f"/api/v1/sessions/{session_id}/turns/advance",
        headers=owner,
        json={"next_character_id": "c1"},
    )
    assert res_adv_dm.status_code == 200
    assert res_adv_dm.json()["status"] == "turn_advanced"


@pytest.mark.asyncio
async def test_live_spicedb_frontdoor_role_assignment_and_checks(
    live_spicedb_endpoint: str | None, trusted_ws_issuer, gateway_tc
):
    """Verify live SpiceDB gRPC connection with Zanzibar schema and frontdoor endpoints."""
    if not live_spicedb_endpoint:
        pytest.skip("Docker unavailable or SpiceDB container failed to start")

    live_client = SpiceDBClient(
        endpoint=live_spicedb_endpoint,
        token="test_live_secret",
    )
    schema_text = await bootstrap_schema(client=live_client)
    assert "definition campaign" in schema_text
    assert "relation dungeon_master: user" in schema_text

    set_spicedb_client(live_client)

    set_session_spicedb(live_client)
    tc = gateway_tc
    dm = _bearer(trusted_ws_issuer, "dm_garrick")
    player = _bearer(trusted_ws_issuer, "player_talia")
    camp_id, session_id = _create_campaign_with_session(tc, dm)

    # Before membership -> 403 Forbidden
    assert tc.get(f"/api/v1/sessions/{session_id}", headers=player).status_code == 403

    # Redeem a player invite through the frontdoor
    _join_with_invite(tc, camp_id, dm, player, role="player")

    # Player can view session but cannot advance turn
    assert tc.get(f"/api/v1/sessions/{session_id}", headers=player).status_code == 200
    res_player_adv = tc.post(
        f"/api/v1/sessions/{session_id}/turns/advance",
        headers=player,
        json={"next_character_id": "char_1"},
    )
    assert res_player_adv.status_code == 403

    # The campaign owner (DM) advances turn
    res_dm_adv = tc.post(
        f"/api/v1/sessions/{session_id}/turns/advance",
        headers=dm,
        json={"next_character_id": "char_1"},
    )
    assert res_dm_adv.status_code == 200
    assert res_dm_adv.json()["status"] == "turn_advanced"

    # Direct permission check via live SpiceDB client
    assert await live_client.check_permission("campaign", camp_id, "view", "user", "player_talia")
    assert not await live_client.check_permission(
        "campaign", camp_id, "run_session", "user", "player_talia"
    )
    assert await live_client.check_permission(
        "campaign", camp_id, "run_session", "user", "dm_garrick"
    )


@pytest.mark.asyncio
async def test_live_spicedb_relationship_deletion_and_revocation(
    live_spicedb_endpoint: str | None, trusted_ws_issuer, gateway_tc
):
    """Verify live tuple deletion instantly revokes permissions in SpiceDB."""
    if not live_spicedb_endpoint:
        pytest.skip("Docker unavailable or SpiceDB container failed to start")

    live_client = SpiceDBClient(
        endpoint=live_spicedb_endpoint,
        token="test_deletion_token",
    )
    await bootstrap_schema(client=live_client)
    set_spicedb_client(live_client)
    set_session_spicedb(live_client)
    tc = gateway_tc

    owner = _bearer(trusted_ws_issuer, "owner_revocation")
    member = _bearer(trusted_ws_issuer, "user_revoked")
    camp_id, session_id = _create_campaign_with_session(tc, owner)

    # Membership through the invite frontdoor -> 200
    _join_with_invite(tc, camp_id, owner, member, role="player")
    assert tc.get(f"/api/v1/sessions/{session_id}", headers=member).status_code == 200

    # Delete the relationship in live SpiceDB and verify immediately denied
    await live_client.delete_relationship(
        resource_type="campaign",
        resource_id=camp_id,
        relation="player",
        subject_type="user",
        subject_id="user_revoked",
    )
    assert tc.get(f"/api/v1/sessions/{session_id}", headers=member).status_code == 403
