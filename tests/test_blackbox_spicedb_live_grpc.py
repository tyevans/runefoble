"""Blackbox TDD frontdoor test suite for live SpiceDB gRPC integration.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object Authorization
- ADR-0005: Kubernetes-First Infrastructure with Helm and Kind
- ADR-0007: Real-Time Voice and Board Synchronization
- ADR-0009: Continuous Backlog Refinement and Technical Debt Management
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from gateway_api.auth import set_spicedb_client
from gateway_api.main import app
from runefoble_auth.bootstrap_schema import bootstrap_schema
from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient


@pytest.mark.asyncio
async def test_mock_spicedb_frontdoor_role_assignment():
    """Verify role assignment and enforcement using MockSpiceDBClient."""
    mock_client = MockSpiceDBClient()
    set_spicedb_client(mock_client)
    tc = TestClient(app)

    camp_id = f"camp-mock-{uuid4().hex[:8]}"
    user_alice = f"user-{uuid4().hex[:6]}"
    user_dm = f"dm-{uuid4().hex[:6]}"

    # Unassigned -> 403 Forbidden
    res = tc.get(f"/api/v1/sessions/{camp_id}", headers={"X-User-Id": user_alice})
    assert res.status_code == 403
    assert res.json()["detail"]["required_permission"] == "view"

    # Assign player role via public gateway endpoint
    res_assign = tc.post(
        f"/api/v1/campaigns/{camp_id}/roles",
        json={"user_id": user_alice, "role": "player"},
    )
    assert res_assign.status_code == 200
    assert res_assign.json()["status"] == "role_assigned"

    # Player can view session but cannot advance turn
    res_view = tc.get(f"/api/v1/sessions/{camp_id}", headers={"X-User-Id": user_alice})
    assert res_view.status_code == 200
    assert res_view.json()["id"] == camp_id

    res_adv = tc.post(
        f"/api/v1/sessions/{camp_id}/turns/advance",
        headers={"X-User-Id": user_alice},
        json={"next_character_id": "c1"},
    )
    assert res_adv.status_code == 403

    # Assign DM role and verify DM can advance turn
    res_assign_dm = tc.post(
        f"/api/v1/campaigns/{camp_id}/roles",
        json={"user_id": user_dm, "role": "dungeon_master"},
    )
    assert res_assign_dm.status_code == 200

    res_adv_dm = tc.post(
        f"/api/v1/sessions/{camp_id}/turns/advance",
        headers={"X-User-Id": user_dm},
        json={"next_character_id": "c1"},
    )
    assert res_adv_dm.status_code == 200
    assert res_adv_dm.json()["status"] == "turn_advanced"


@pytest.mark.asyncio
async def test_live_spicedb_frontdoor_role_assignment_and_checks(
    live_spicedb_endpoint: str | None,
):
    """Verify live SpiceDB gRPC connection with Zanzibar schema and frontdoor endpoints."""
    if not live_spicedb_endpoint:
        pytest.skip("Docker unavailable or SpiceDB container failed to start")

    live_client = SpiceDBClient(
        endpoint=live_spicedb_endpoint,
        token="test_live_secret",
        use_mock=False,
    )
    schema_text = await bootstrap_schema(client=live_client)
    assert "definition campaign" in schema_text
    assert "relation dungeon_master: user" in schema_text

    set_spicedb_client(live_client)
    tc = TestClient(app)
    camp_id = f"camp-live-{uuid4().hex[:8]}"
    player_id = "player_talia"
    dm_id = "dm_garrick"

    # Before assignment -> 403 Forbidden
    assert (
        tc.get(f"/api/v1/sessions/{camp_id}", headers={"X-User-Id": player_id}).status_code == 403
    )

    # Assign player role via Gateway API
    res_role = tc.post(
        f"/api/v1/campaigns/{camp_id}/roles",
        json={"user_id": player_id, "role": "player"},
    )
    assert res_role.status_code == 200
    assert res_role.json()["status"] == "role_assigned"

    # Player can view session but cannot advance turn
    assert (
        tc.get(f"/api/v1/sessions/{camp_id}", headers={"X-User-Id": player_id}).status_code == 200
    )
    res_player_adv = tc.post(
        f"/api/v1/sessions/{camp_id}/turns/advance",
        headers={"X-User-Id": player_id},
        json={"next_character_id": "char_1"},
    )
    assert res_player_adv.status_code == 403

    # Assign DM role via Gateway API and advance turn
    res_dm_role = tc.post(
        f"/api/v1/campaigns/{camp_id}/roles",
        json={"user_id": dm_id, "role": "dungeon_master"},
    )
    assert res_dm_role.status_code == 200

    res_dm_adv = tc.post(
        f"/api/v1/sessions/{camp_id}/turns/advance",
        headers={"X-User-Id": dm_id},
        json={"next_character_id": "char_1"},
    )
    assert res_dm_adv.status_code == 200
    assert res_dm_adv.json()["status"] == "turn_advanced"

    # Direct permission check via live SpiceDB client
    assert await live_client.check_permission("campaign", camp_id, "view", "user", player_id)
    assert not await live_client.check_permission(
        "campaign", camp_id, "run_session", "user", player_id
    )
    assert await live_client.check_permission("campaign", camp_id, "run_session", "user", dm_id)


@pytest.mark.asyncio
async def test_live_spicedb_relationship_deletion_and_revocation(
    live_spicedb_endpoint: str | None,
):
    """Verify live tuple deletion instantly revokes permissions in SpiceDB."""
    if not live_spicedb_endpoint:
        pytest.skip("Docker unavailable or SpiceDB container failed to start")

    live_client = SpiceDBClient(
        endpoint=live_spicedb_endpoint,
        token="test_deletion_token",
        use_mock=False,
    )
    await bootstrap_schema(client=live_client)
    set_spicedb_client(live_client)
    tc = TestClient(app)

    camp_id = f"camp-del-{uuid4().hex[:8]}"
    user_id = "user_revoked"

    # Grant player role and verify allowed
    tc.post(
        f"/api/v1/campaigns/{camp_id}/roles",
        json={"user_id": user_id, "role": "player"},
    )
    assert tc.get(f"/api/v1/sessions/{camp_id}", headers={"X-User-Id": user_id}).status_code == 200

    # Delete relationship in live SpiceDB and verify immediately denied
    await live_client.delete_relationship(
        resource_type="campaign",
        resource_id=camp_id,
        relation="player",
        subject_type="user",
        subject_id=user_id,
    )
    assert tc.get(f"/api/v1/sessions/{camp_id}", headers={"X-User-Id": user_id}).status_code == 403
