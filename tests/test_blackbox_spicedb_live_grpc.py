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

import os
from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app
from runefoble_auth.bootstrap_schema import bootstrap_schema
from runefoble_auth.spicedb import SpiceDBClient

from tests.helpers.campaign_setup import create_campaign, create_owner_session, invite_and_join
from tests.helpers.spicedb_factory import shared_spicedb_client
from tests.helpers.ws_identity import bearer


@pytest.fixture
def gateway_tc(game_session_upstream) -> Iterator[TestClient]:
    """Gateway client with the lifespan entered after game_session is served."""
    with TestClient(app) as gateway_client:
        yield gateway_client


@pytest.mark.asyncio
async def test_mock_spicedb_frontdoor_role_assignment(trusted_ws_issuer, gateway_tc):
    """Verify invite-based membership and enforcement using the strict mock SpiceDB client."""
    tc = gateway_tc

    owner_id = f"owner-{uuid4().hex[:6]}"

    owner = bearer(owner_id, issuer=trusted_ws_issuer)
    user_alice_id = f"user-{uuid4().hex[:6]}"
    user_alice = bearer(user_alice_id, issuer=trusted_ws_issuer)
    camp_id = create_campaign(tc, owner_id)
    session_id = create_owner_session(os.environ["RUNEFOBLE_GAME_SESSION_URL"], owner, camp_id)

    # Not a member -> 403 Forbidden
    res = tc.get(f"/api/v1/sessions/{session_id}", headers=user_alice)
    assert res.status_code == 403
    assert res.json()["detail"]["required_permission"] == "observe"

    # Redeem a player invite
    invite_and_join(tc, camp_id, owner_id, user_alice_id, role="player")

    # Player can view session but cannot advance turn
    res_view = tc.get(f"/api/v1/sessions/{session_id}", headers=user_alice)
    assert res_view.status_code == 200
    assert res_view.json()["session_id"] == session_id

    res_adv = tc.post(
        f"/api/v1/sessions/{session_id}/turns/advance",
        headers=user_alice,
        json={"next_character_id": "c1"},
    )
    assert res_adv.status_code == 403

    # The owner runs the session as DM and can advance turn
    assert tc.post(f"/api/v1/sessions/{session_id}/start", headers=owner).status_code == 200
    res_adv_dm = tc.post(
        f"/api/v1/sessions/{session_id}/turns/advance",
        headers=owner,
        json={"next_character_id": "c1"},
    )
    assert res_adv_dm.status_code == 200
    assert tc.get(f"/api/v1/sessions/{session_id}", headers=owner).json()["current_turn"] == 2


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

    with shared_spicedb_client(live_client):
        tc = gateway_tc
        dm_id = "dm_garrick"
        dm = bearer(dm_id, issuer=trusted_ws_issuer)
        player_id = "player_talia"
        player = bearer(player_id, issuer=trusted_ws_issuer)
        camp_id = create_campaign(tc, dm_id)
        session_id = create_owner_session(os.environ["RUNEFOBLE_GAME_SESSION_URL"], dm, camp_id)

        # Before membership -> 403 Forbidden
        assert tc.get(f"/api/v1/sessions/{session_id}", headers=player).status_code == 403

        # Redeem a player invite through the frontdoor
        invite_and_join(tc, camp_id, dm_id, player_id, role="player")

        # Player can view session but cannot advance turn
        assert tc.get(f"/api/v1/sessions/{session_id}", headers=player).status_code == 200
        res_player_adv = tc.post(
            f"/api/v1/sessions/{session_id}/turns/advance",
            headers=player,
            json={"next_character_id": "char_1"},
        )
        assert res_player_adv.status_code == 403

        # The campaign owner (DM) starts the session and advances the turn
        assert tc.post(f"/api/v1/sessions/{session_id}/start", headers=dm).status_code == 200
        res_dm_adv = tc.post(
            f"/api/v1/sessions/{session_id}/turns/advance",
            headers=dm,
            json={"next_character_id": "char_1"},
        )
        assert res_dm_adv.status_code == 200
        assert tc.get(f"/api/v1/sessions/{session_id}", headers=dm).json()["current_turn"] == 2

        # Direct permission check via live SpiceDB client
        assert await live_client.check_permission(
            "campaign", camp_id, "view", "user", "player_talia"
        )
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
    with shared_spicedb_client(live_client):
        tc = gateway_tc

        owner_id = "owner_revocation"

        owner = bearer(owner_id, issuer=trusted_ws_issuer)
        member_id = "user_revoked"
        member = bearer(member_id, issuer=trusted_ws_issuer)
        camp_id = create_campaign(tc, owner_id)
        session_id = create_owner_session(os.environ["RUNEFOBLE_GAME_SESSION_URL"], owner, camp_id)

        # Membership through the invite frontdoor -> 200
        invite_and_join(tc, camp_id, owner_id, member_id, role="player")
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
