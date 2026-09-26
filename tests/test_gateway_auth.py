"""Tests for Gateway API Zanzibar object-level authorization."""

import pytest
from fastapi.testclient import TestClient
from gateway_api.auth import get_spicedb_client
from gateway_api.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_zanzibar_authorization_enforcement():
    """Verify that Gateway API enforces SpiceDB Zanzibar permissions without hardcoded role checks."""
    campaign_id = "camp-auth-101"

    # 1. Unassigned user tries to view session -> 403 Forbidden
    res_unauth = client.get(
        f"/api/v1/sessions/{campaign_id}",
        headers={"X-User-Id": "stranger_bob"},
    )
    assert res_unauth.status_code == 403
    err_data = res_unauth.json()["detail"]
    assert err_data["error"] == "permission_denied"
    assert err_data["required_permission"] == "view"

    # 2. Assign 'player' role in Zanzibar
    res_assign_player = client.post(
        f"/api/v1/campaigns/{campaign_id}/roles",
        json={"user_id": "player_alice", "role": "player"},
    )
    assert res_assign_player.status_code == 200

    # 3. Player can now view session
    res_player_view = client.get(
        f"/api/v1/sessions/{campaign_id}",
        headers={"X-User-Id": "player_alice"},
    )
    assert res_player_view.status_code == 200
    assert res_player_view.json()["id"] == campaign_id

    # 4. Player tries to advance turn (requires 'run_session' / DM) -> 403 Forbidden
    res_player_advance = client.post(
        f"/api/v1/sessions/{campaign_id}/turns/advance",
        headers={"X-User-Id": "player_alice"},
        json={"next_character_id": "c2"},
    )
    assert res_player_advance.status_code == 403
    assert res_player_advance.json()["detail"]["required_permission"] == "run_session"

    # 5. Assign 'dungeon_master' role to DM Evelyn
    res_assign_dm = client.post(
        f"/api/v1/campaigns/{campaign_id}/roles",
        json={"user_id": "dm_evelyn", "role": "dungeon_master"},
    )
    assert res_assign_dm.status_code == 200

    # 6. DM Evelyn can advance turn successfully
    res_dm_advance = client.post(
        f"/api/v1/sessions/{campaign_id}/turns/advance",
        headers={"X-User-Id": "dm_evelyn"},
        json={"next_character_id": "c2"},
    )
    assert res_dm_advance.status_code == 200
    assert res_dm_advance.json()["status"] == "turn_advanced"


@pytest.mark.asyncio
async def test_zanzibar_board_view_permission():
    """Verify board query endpoint requires Zanzibar view permission."""
    campaign_id = "camp-board-202"
    spicedb = get_spicedb_client()

    # Grant view to spectator
    await spicedb.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="view",
        subject_type="user",
        subject_id="spectator_devon",
    )

    res = client.get(
        f"/api/v1/boards/{campaign_id}",
        headers={"X-User-Id": "spectator_devon"},
    )
    assert res.status_code == 200
    assert "tokens" in res.json()
