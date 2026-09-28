"""Blackbox frontdoor tests for Campaign Creation, Ownership, and Invites (US-0063).

Governed by ADR-0001, ADR-0003, and Hard Invariants 6 and 7.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from gateway_api.auth import get_spicedb_client


@pytest.mark.asyncio
async def test_campaign_creation_ownership_and_access_control(client_gw: TestClient):
    """Verify campaign creation assigns Zanzibar owner relation and guards access."""
    headers_evelyn = {"X-User-Id": "dm_evelyn"}
    spicedb = get_spicedb_client()

    # 1. Evelyn creates campaign via public frontdoor POST /api/v1/campaigns
    res = client_gw.post(
        "/api/v1/campaigns",
        json={"title": "Shadows of Drakkenheim", "setting": "Gothic Fantasy"},
        headers=headers_evelyn,
    )
    assert res.status_code == 201
    camp = res.json()
    campaign_id = camp["id"]
    assert camp["title"] == "Shadows of Drakkenheim"
    assert camp["role"] == "owner"
    assert camp["owner_id"] == "dm_evelyn"

    # 2. Evelyn is granted owner, manage, run_session, and view in SpiceDB Zanzibar
    assert await spicedb.check_permission("campaign", campaign_id, "manage", "user", "dm_evelyn")
    assert await spicedb.check_permission(
        "campaign", campaign_id, "run_session", "user", "dm_evelyn"
    )
    assert await spicedb.check_permission("campaign", campaign_id, "view", "user", "dm_evelyn")

    # 3. Evelyn can inspect details; unauthorized stranger receives 403 Forbidden
    assert (
        client_gw.get(f"/api/v1/campaigns/{campaign_id}", headers=headers_evelyn).status_code == 200
    )
    res_stranger = client_gw.get(
        f"/api/v1/campaigns/{campaign_id}", headers={"X-User-Id": "stranger_bob"}
    )
    assert res_stranger.status_code == 403
    assert res_stranger.json()["detail"]["error"] == "permission_denied"


@pytest.mark.asyncio
async def test_campaign_invite_redemption_and_role_assignment(client_gw: TestClient):
    """Verify shareable invite token lifecycle, redemption, and Zanzibar role sync."""
    headers_dm = {"X-User-Id": "dm_evelyn"}
    headers_marcus = {"X-User-Id": "player_marcus"}
    spicedb = get_spicedb_client()

    # Setup: Create campaign
    create_res = client_gw.post(
        "/api/v1/campaigns", json={"title": "Star-Eater Odyssey"}, headers=headers_dm
    )
    camp_id = create_res.json()["id"]

    # 1. Non-manager is forbidden from generating invites
    res_unauth = client_gw.post(
        f"/api/v1/campaigns/{camp_id}/invites",
        json={"role": "player"},
        headers={"X-User-Id": "stranger_bob"},
    )
    assert res_unauth.status_code == 403

    # 2. DM generates shareable player invite token
    invite_res = client_gw.post(
        f"/api/v1/campaigns/{camp_id}/invites",
        json={"role": "player", "max_uses": 2, "expires_in_hours": 48},
        headers=headers_dm,
    )
    assert invite_res.status_code == 201
    token = invite_res.json()["token"]

    # 3. Marcus redeems invite token via POST /api/v1/campaigns/join
    join_res = client_gw.post(
        "/api/v1/campaigns/join", json={"invite_token": token}, headers=headers_marcus
    )
    assert join_res.status_code == 200
    assert join_res.json()["status"] == "joined"
    assert join_res.json()["role"] == "player"

    # 4. DM updates/assigns Zanzibar role tuple explicitly
    role_res = client_gw.post(
        f"/api/v1/campaigns/{camp_id}/roles",
        json={"user_id": "player_marcus", "role": "player"},
        headers=headers_dm,
    )
    assert role_res.status_code == 200

    # 5. Member roster listing reflects both members and roles
    members_res = client_gw.get(f"/api/v1/campaigns/{camp_id}/members", headers=headers_marcus)
    assert members_res.status_code == 200
    roles_map = {m["user_id"]: m["role"] for m in members_res.json()}
    assert roles_map.get("dm_evelyn") == "owner"
    assert roles_map.get("player_marcus") == "player"

    # 6. Verify Zanzibar permissions: Marcus has play & view, but not manage
    assert await spicedb.check_permission("campaign", camp_id, "play", "user", "player_marcus")
    assert await spicedb.check_permission("campaign", camp_id, "view", "user", "player_marcus")
    assert not await spicedb.check_permission(
        "campaign", camp_id, "manage", "user", "player_marcus"
    )
