"""Blackbox frontdoor tests for Gateway Campaign Lifecycle and Membership API (TASK-0208).

Governing ADRs: ADR-0001 (SpiceDB Zanzibar), ADR-0005 (Zitadel OIDC), ADR-0007 (Domain-Driven Gateway).
Verifies:
1. Campaign creation and automatic SpiceDB Zanzibar ownership assignment.
2. Campaign listing filtered strictly by Zanzibar view permission.
3. Campaign detail retrieval and PATCH updates with Zanzibar manage permission enforcement.
4. Shareable invite token generation, single-use/multi-use limits, and join workflow.
5. Zanzibar role assignment, member roster listing, and spectator read-only access.
"""

import pytest
from fastapi.testclient import TestClient
from gateway_api.campaign_store import campaign_store
from gateway_api.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_store():
    """Reset campaign and invite memory store before each test."""
    campaign_store.reset()
    yield


@pytest.mark.asyncio
async def test_campaign_creation_and_ownership():
    """Verify POST /api/v1/campaigns registers campaign and assigns owner role in SpiceDB."""
    headers_evelyn = {"X-User-Id": "dm_evelyn"}

    create_payload = {
        "title": "Shadows of Drakkenheim",
        "description": "Gothic horror urban exploration.",
        "setting": "Gothic Fantasy",
        "system": "5e",
        "settings": {"ruleset": "2024", "gritty_realism": True},
    }

    res_create = client.post("/api/v1/campaigns", json=create_payload, headers=headers_evelyn)
    assert res_create.status_code == 201
    camp_data = res_create.json()
    campaign_id = camp_data["id"]

    assert camp_data["title"] == "Shadows of Drakkenheim"
    assert camp_data["setting"] == "Gothic Fantasy"
    assert camp_data["system"] == "5e"
    assert camp_data["role"] == "owner"
    assert camp_data["owner_id"] == "dm_evelyn"
    assert camp_data["member_count"] >= 1
    assert camp_data["settings"]["gritty_realism"] is True

    # Owner can view campaign details
    res_get = client.get(f"/api/v1/campaigns/{campaign_id}", headers=headers_evelyn)
    assert res_get.status_code == 200
    assert res_get.json()["title"] == "Shadows of Drakkenheim"

    # Unrelated user without Zanzibar permissions is denied access
    headers_stranger = {"X-User-Id": "stranger_bob"}
    res_denied = client.get(f"/api/v1/campaigns/{campaign_id}", headers=headers_stranger)
    assert res_denied.status_code == 403
    assert res_denied.json()["detail"]["error"] == "permission_denied"


@pytest.mark.asyncio
async def test_campaign_listing_isolation():
    """Verify GET /api/v1/campaigns lists only campaigns where the user has Zanzibar view permission."""
    headers_evelyn = {"X-User-Id": "dm_evelyn"}
    headers_marcus = {"X-User-Id": "player_marcus"}

    # Evelyn creates Campaign A
    res_a = client.post(
        "/api/v1/campaigns",
        json={"title": "Evelyn's Tale", "setting": "Grimdark"},
        headers=headers_evelyn,
    )
    assert res_a.status_code == 201
    camp_a_id = res_a.json()["id"]

    # Marcus creates Campaign B
    res_b = client.post(
        "/api/v1/campaigns",
        json={"title": "Marcus's Odyssey", "setting": "High Fantasy"},
        headers=headers_marcus,
    )
    assert res_b.status_code == 201
    camp_b_id = res_b.json()["id"]

    # Evelyn's list contains only Campaign A
    evelyn_list = client.get("/api/v1/campaigns", headers=headers_evelyn).json()
    evelyn_ids = [c["id"] for c in evelyn_list]
    assert camp_a_id in evelyn_ids
    assert camp_b_id not in evelyn_ids

    # Marcus's list contains only Campaign B
    marcus_list = client.get("/api/v1/campaigns", headers=headers_marcus).json()
    marcus_ids = [c["id"] for c in marcus_list]
    assert camp_b_id in marcus_ids
    assert camp_a_id not in marcus_ids


@pytest.mark.asyncio
async def test_campaign_patch_manage_permission():
    """Verify PATCH /api/v1/campaigns/{id} requires Zanzibar manage permission."""
    headers_evelyn = {"X-User-Id": "dm_evelyn"}
    headers_marcus = {"X-User-Id": "player_marcus"}

    res_create = client.post(
        "/api/v1/campaigns",
        json={"title": "Original Title", "description": "Original Desc"},
        headers=headers_evelyn,
    )
    camp_id = res_create.json()["id"]

    # Marcus (no permission) attempts PATCH -> 403 Forbidden
    res_fail = client.patch(
        f"/api/v1/campaigns/{camp_id}",
        json={"title": "Hacked Title"},
        headers=headers_marcus,
    )
    assert res_fail.status_code == 403

    # Evelyn (owner / manage) updates campaign successfully
    res_patch = client.patch(
        f"/api/v1/campaigns/{camp_id}",
        json={"title": "Refined Drakkenheim", "description": "Updated lore."},
        headers=headers_evelyn,
    )
    assert res_patch.status_code == 200
    updated_data = res_patch.json()
    assert updated_data["title"] == "Refined Drakkenheim"
    assert updated_data["description"] == "Updated lore."


@pytest.mark.asyncio
async def test_invite_generation_and_joining_workflow():
    """Verify invite creation, redemption, and membership registration in SpiceDB."""
    headers_evelyn = {"X-User-Id": "dm_evelyn"}
    headers_marcus = {"X-User-Id": "player_marcus"}

    # 1. Evelyn creates campaign
    res_create = client.post(
        "/api/v1/campaigns",
        json={"title": "Dungeon Delve", "setting": "Undermountain"},
        headers=headers_evelyn,
    )
    camp_id = res_create.json()["id"]

    # 2. Stranger cannot create invite -> 403 Forbidden
    headers_stranger = {"X-User-Id": "random_stranger"}
    res_unauth_invite = client.post(
        f"/api/v1/campaigns/{camp_id}/invites",
        json={"role": "player"},
        headers=headers_stranger,
    )
    assert res_unauth_invite.status_code == 403

    # 3. Evelyn (owner / run_session) creates player invite token
    res_invite = client.post(
        f"/api/v1/campaigns/{camp_id}/invites",
        json={"role": "player", "expires_in_hours": 24, "max_uses": 2},
        headers=headers_evelyn,
    )
    assert res_invite.status_code == 201
    invite_data = res_invite.json()
    token = invite_data["token"]
    assert invite_data["role"] == "player"
    assert f"/#/join/{token}" in invite_data["invite_url"]

    # 4. Marcus joins campaign using invite token
    res_join = client.post(
        "/api/v1/campaigns/join",
        json={"invite_token": token},
        headers=headers_marcus,
    )
    assert res_join.status_code == 200
    join_data = res_join.json()
    assert join_data["status"] == "joined"
    assert join_data["campaign_id"] == camp_id
    assert join_data["user_id"] == "player_marcus"
    assert join_data["role"] == "player"

    # 5. Marcus can now view campaign and appears on members roster
    res_marcus_view = client.get(f"/api/v1/campaigns/{camp_id}", headers=headers_marcus)
    assert res_marcus_view.status_code == 200

    res_members = client.get(f"/api/v1/campaigns/{camp_id}/members", headers=headers_marcus)
    assert res_members.status_code == 200
    members = res_members.json()
    member_roles = {(m["user_id"], m["role"]) for m in members}
    assert ("dm_evelyn", "owner") in member_roles
    assert ("player_marcus", "player") in member_roles

    # 6. Invalid token rejection
    res_bad_join = client.post(
        "/api/v1/campaigns/join",
        json={"invite_token": "nonexistent_token_xyz"},
        headers=headers_marcus,
    )
    assert res_bad_join.status_code == 400
    assert res_bad_join.json()["detail"]["error"] == "invalid_invite"


@pytest.mark.asyncio
async def test_spectator_invite_and_usage_limit():
    """Verify spectator role invitation and max_uses exhaustion."""
    headers_dm = {"X-User-Id": "dm_sarah"}
    headers_viewer1 = {"X-User-Id": "viewer_devon"}
    headers_viewer2 = {"X-User-Id": "viewer_clara"}

    # DM creates campaign
    res_create = client.post(
        "/api/v1/campaigns",
        json={"title": "Streaming Arena"},
        headers=headers_dm,
    )
    camp_id = res_create.json()["id"]

    # Create single-use spectator invite
    res_invite = client.post(
        f"/api/v1/campaigns/{camp_id}/invites",
        json={"role": "spectator", "max_uses": 1},
        headers=headers_dm,
    )
    assert res_invite.status_code == 201
    token = res_invite.json()["token"]

    # Viewer 1 joins successfully
    res_join1 = client.post(
        "/api/v1/campaigns/join",
        json={"invite_token": token},
        headers=headers_viewer1,
    )
    assert res_join1.status_code == 200
    assert res_join1.json()["role"] == "spectator"

    # Viewer 2 attempts to use exhausted token -> 400 Bad Request
    res_join2 = client.post(
        "/api/v1/campaigns/join",
        json={"invite_token": token},
        headers=headers_viewer2,
    )
    assert res_join2.status_code == 400
    assert "limit reached" in res_join2.json()["detail"]["message"].lower()

    # Viewer 1 has spectator access: can view session, cannot advance turns
    res_sess = client.get(f"/api/v1/sessions/{camp_id}", headers=headers_viewer1)
    assert res_sess.status_code == 200

    res_advance = client.post(
        f"/api/v1/sessions/{camp_id}/turns/advance",
        json={"next_character_id": "c1"},
        headers=headers_viewer1,
    )
    assert res_advance.status_code == 403
