"""Blackbox frontdoor tests for Campaign Roster, Roles & Zanzibar Membership Lifecycle (TASK-0353).

Governed by ADR-0001 (SpiceDB Zanzibar), ADR-0004 (Lit Web Components), ADR-0013 (Microfrontends).
Hard Invariants:
- Hard Invariant 1: Object-level authorization via SpiceDB Zanzibar schema.
- Hard Invariant 6: File length limit (< 500 lines).
- Hard Invariant 7: Blackbox TDD with frontdoor setup.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from gateway_api.auth import get_spicedb_client
from gateway_api.campaign_store import campaign_store
from gateway_api.character_store import character_store
from gateway_api.main import app as gateway_app


@pytest.fixture(autouse=True)
def reset_stores():
    campaign_store.reset()
    character_store.reset()
    yield


@pytest.fixture
def client_gw() -> TestClient:
    return TestClient(gateway_app)


@pytest.mark.asyncio
async def test_campaign_member_removal_endpoint_requires_manage_permission(client_gw: TestClient):
    """Verify DELETE /api/v1/campaigns/{id}/members/{user_id} enforces Zanzibar manage permission."""
    headers_dm = {"X-User-Id": "dm_evelyn"}
    headers_stranger = {"X-User-Id": "stranger_bob"}
    headers_player = {"X-User-Id": "player_marcus"}
    spicedb = get_spicedb_client()

    # 1. DM creates campaign
    res = client_gw.post(
        "/api/v1/campaigns",
        json={"title": "Roster Test Campaign", "setting": "Sword Coast"},
        headers=headers_dm,
    )
    assert res.status_code == 201
    camp_id = res.json()["id"]

    # 2. DM generates invite and player joins
    inv_res = client_gw.post(
        f"/api/v1/campaigns/{camp_id}/invites",
        json={"role": "player"},
        headers=headers_dm,
    )
    assert inv_res.status_code == 201
    token = inv_res.json()["token"]

    join_res = client_gw.post(
        "/api/v1/campaigns/join",
        json={"invite_token": token},
        headers=headers_player,
    )
    assert join_res.status_code == 200

    # 3. Marcus has view and play permissions
    assert await spicedb.check_permission("campaign", camp_id, "view", "user", "player_marcus")
    assert await spicedb.check_permission("campaign", camp_id, "play", "user", "player_marcus")

    # 4. Unauthorized stranger attempts to remove player Marcus -> 403 Forbidden
    unauth_res = client_gw.delete(
        f"/api/v1/campaigns/{camp_id}/members/player_marcus",
        headers=headers_stranger,
    )
    assert unauth_res.status_code == 403

    # 5. Regular player Marcus attempts to remove DM Evelyn -> 403 Forbidden (no manage)
    player_remove_res = client_gw.delete(
        f"/api/v1/campaigns/{camp_id}/members/dm_evelyn",
        headers=headers_player,
    )
    assert player_remove_res.status_code == 403

    # 6. DM Evelyn removes player Marcus via DELETE /api/v1/campaigns/{id}/members/{user_id}
    del_res = client_gw.delete(
        f"/api/v1/campaigns/{camp_id}/members/player_marcus",
        headers=headers_dm,
    )
    assert del_res.status_code == 200
    data = del_res.json()
    assert data["status"] == "member_removed"
    assert data["campaign_id"] == camp_id
    assert data["user_id"] == "player_marcus"

    # 7. Marcus's Zanzibar permissions on the campaign are purged
    assert not await spicedb.check_permission("campaign", camp_id, "view", "user", "player_marcus")
    assert not await spicedb.check_permission("campaign", camp_id, "play", "user", "player_marcus")

    # 8. Marcus is no longer in GET /api/v1/campaigns/{id}/members
    members_res = client_gw.get(f"/api/v1/campaigns/{camp_id}/members", headers=headers_dm)
    assert members_res.status_code == 200
    member_ids = [m["user_id"] for m in members_res.json()]
    assert "player_marcus" not in member_ids


@pytest.mark.asyncio
async def test_campaign_member_enrichment_with_character_and_username(client_gw: TestClient):
    """Verify get_campaign_members populates username and character_name from characters."""
    headers_dm = {"X-User-Id": "dm_evelyn"}
    headers_marcus = {"X-User-Id": "player_marcus"}

    # 1. DM creates campaign
    res = client_gw.post(
        "/api/v1/campaigns",
        json={"title": "Astral Expanse", "setting": "Astral Plane"},
        headers=headers_dm,
    )
    assert res.status_code == 201
    camp_id = res.json()["id"]

    # 2. Marcus creates character and assigns it to campaign
    char_res = client_gw.post(
        "/api/v1/characters",
        json={
            "name": "Marcus Aurelius the Paladin",
            "character_class": "Paladin",
            "campaign_id": camp_id,
        },
        headers=headers_marcus,
    )
    assert char_res.status_code == 201

    # 3. DM invites Marcus as player
    inv_res = client_gw.post(
        f"/api/v1/campaigns/{camp_id}/invites",
        json={"role": "player"},
        headers=headers_dm,
    )
    assert inv_res.status_code == 201
    token = inv_res.json()["token"]

    join_res = client_gw.post(
        "/api/v1/campaigns/join",
        json={"invite_token": token},
        headers=headers_marcus,
    )
    assert join_res.status_code == 200

    # 4. Query campaign members
    members_res = client_gw.get(f"/api/v1/campaigns/{camp_id}/members", headers=headers_dm)
    assert members_res.status_code == 200
    members = members_res.json()

    marcus_member = next((m for m in members if m["user_id"] == "player_marcus"), None)
    assert marcus_member is not None
    assert marcus_member["role"] == "player"
    assert marcus_member["username"] == "Marcus"
    assert marcus_member["character_name"] == "Marcus Aurelius the Paladin"

    evelyn_member = next((m for m in members if m["user_id"] == "dm_evelyn"), None)
    assert evelyn_member is not None
    assert evelyn_member["role"] == "owner"
    assert evelyn_member["username"] == "Evelyn Vance"


@pytest.mark.asyncio
async def test_campaign_member_role_mutation_and_purge_lifecycle(client_gw: TestClient):
    """Verify changing roles between spectator and dungeon_master and subsequent member removal."""
    headers_dm = {"X-User-Id": "dm_evelyn"}
    headers_cadence = {"X-User-Id": "player_cadence"}
    spicedb = get_spicedb_client()

    # 1. Create campaign
    create_res = client_gw.post(
        "/api/v1/campaigns",
        json={"title": "Citadel of Secrets"},
        headers=headers_dm,
    )
    camp_id = create_res.json()["id"]

    # 2. Invite as spectator
    inv_res = client_gw.post(
        f"/api/v1/campaigns/{camp_id}/invites",
        json={"role": "spectator"},
        headers=headers_dm,
    )
    token = inv_res.json()["token"]
    client_gw.post("/api/v1/campaigns/join", json={"invite_token": token}, headers=headers_cadence)

    # 3. Cadence has view but not play
    assert await spicedb.check_permission("campaign", camp_id, "view", "user", "player_cadence")
    assert not await spicedb.check_permission("campaign", camp_id, "play", "user", "player_cadence")

    # 4. DM promotes Cadence to player
    role_res = client_gw.post(
        f"/api/v1/campaigns/{camp_id}/roles",
        json={"user_id": "player_cadence", "role": "player"},
        headers=headers_dm,
    )
    assert role_res.status_code == 200
    assert await spicedb.check_permission("campaign", camp_id, "play", "user", "player_cadence")

    # 5. DM removes Cadence
    del_res = client_gw.delete(
        f"/api/v1/campaigns/{camp_id}/members/player_cadence",
        headers=headers_dm,
    )
    assert del_res.status_code == 200

    # 6. Cadence no longer has any permissions
    assert not await spicedb.check_permission("campaign", camp_id, "view", "user", "player_cadence")
    assert not await spicedb.check_permission("campaign", camp_id, "play", "user", "player_cadence")


def test_source_file_length_limits():
    """Verify Hard Invariant 6: All files touched satisfy file length limits (< 500 lines)."""
    root = Path(__file__).resolve().parent.parent
    files = [
        root / "gateway" / "api" / "src" / "gateway_api" / "routers" / "campaigns.py",
        root / "gateway" / "api" / "src" / "gateway_api" / "campaign_store" / "queries.py",
        root / "frontend" / "src" / "services" / "app-data-service.ts",
        root / "frontend" / "src" / "services" / "app-data-service.fixtures.ts",
        root / "frontend" / "src" / "runefoble-app.ts",
        Path(__file__),
    ]
    for f in files:
        assert f.is_file(), f"Expected file {f} to exist"
        line_count = len(f.read_text(encoding="utf-8").splitlines())
        assert line_count < 500, f"File {f.name} has {line_count} lines (exceeds 500)"
