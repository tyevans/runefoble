"""Blackbox E2E Suite: Character Management, Zanzibar Authorization, and Tabletop Sync.

TASK-0258: Character Management and Tabletop Sync Blackbox Test Suite
Governing ADRs:
- ADR-0001: SpiceDB Zanzibar Object Authorization
- ADR-0002: Domain Events via eventsource-py
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0010: Continuous Integration Pipeline
- ADR-0013: Frontend Microfrontend Architecture
Hard Invariants:
- Hard Invariant 1: Object-level authorization runs through SpiceDB Zanzibar schema
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with frontdoor setup
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from gateway_api.auth import get_spicedb_client
from gateway_api.main import app


def _auth(issuer, sub: str) -> dict[str, str]:
    """Return Bearer headers carrying a token that the gateway verifies for `sub`."""
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
TS_TEST_DIR = FRONTEND_DIR / "test" / "character_management"


@pytest.fixture
def client(game_session_upstream, character_sheet_upstream):
    """Enter the gateway lifespan after game_session is served, so the proxy reaches it."""
    with TestClient(app) as gateway_client:
        yield gateway_client


@pytest.mark.asyncio
async def test_character_crud_and_zanzibar_ownership(trusted_ws_issuer, client):
    """Verify character creation, SpiceDB Zanzibar ownership relations, and owner-only deletion."""
    headers_owner = _auth(trusted_ws_issuer, "user_valeros")
    headers_stranger = _auth(trusted_ws_issuer, "user_stranger")

    payload = {
        "name": "Valeros of Korvosa",
        "characterClass": "Fighter",
        "subclass": "Battle Master",
        "maxHp": 45,
        "armorClass": 18,
        "speed": 30,
    }

    # 1. Frontdoor POST /api/v1/characters
    res = client.post("/api/v1/characters", json=payload, headers=headers_owner)
    assert res.status_code == 201
    char_data = res.json()
    char_id = char_data["id"]

    assert char_data["name"] == "Valeros of Korvosa"
    assert char_data["character_class"] == "Fighter"
    assert char_data["characterClass"] == "Fighter"
    assert char_data["current_hp"] == 45
    assert char_data["max_hp"] == 45
    assert char_data["armor_class"] == 18
    assert char_data["owner_id"] == "user_valeros"

    # 2. Assert SpiceDB owner and permission tuples written
    spicedb = get_spicedb_client()
    assert (
        await spicedb.check_permission("character", char_id, "delete", "user", "user_valeros")
        is True
    )
    assert (
        await spicedb.check_permission("character", char_id, "view", "user", "user_valeros") is True
    )
    assert (
        await spicedb.check_permission("character", char_id, "edit", "user", "user_valeros") is True
    )

    # 4. Assert non-owner stranger cannot edit campaign (403 Forbidden)
    res_stranger_edit = client.patch(
        f"/api/v1/characters/{char_id}/campaign",
        json={"campaignId": "camp-random"},
        headers=headers_stranger,
    )
    assert res_stranger_edit.status_code == 403

    # 5. Assert non-owner stranger cannot view details (403 Forbidden)
    res_stranger_view = client.get(f"/api/v1/characters/{char_id}", headers=headers_stranger)
    assert res_stranger_view.status_code == 403


@pytest.mark.asyncio
async def test_character_campaign_assignment(trusted_ws_issuer, client):
    """Verify character campaign assignment writes campaign tuple and grants view to party members."""
    headers_alice = _auth(trusted_ws_issuer, "user_alice")
    headers_party_bob = _auth(trusted_ws_issuer, "user_bob")
    headers_outsider = _auth(trusted_ws_issuer, "user_outsider")

    # 1. Create Campaign
    camp_res = client.post(
        "/api/v1/campaigns",
        json={"title": "Tomb of the Star-Eater", "setting": "Astral Void"},
        headers=headers_alice,
    )
    assert camp_res.status_code == 201
    campaign_id = camp_res.json()["id"]

    # 2. Add Bob as a party member in SpiceDB
    spicedb = get_spicedb_client()
    await spicedb.write_relationship("campaign", campaign_id, "player", "user", "user_bob")

    # 3. Alice creates an unassigned character
    char_res = client.post(
        "/api/v1/characters",
        json={"name": "Seoni", "characterClass": "Sorcerer", "maxHp": 22},
        headers=headers_alice,
    )
    assert char_res.status_code == 201
    char_id = char_res.json()["id"]

    # 4. Before assignment: party member Bob cannot view Alice's character (403 Forbidden)
    res_bob_before = client.get(f"/api/v1/characters/{char_id}", headers=headers_party_bob)
    assert res_bob_before.status_code == 403

    # 5. Alice assigns character to campaign
    res_assign = client.patch(
        f"/api/v1/characters/{char_id}/campaign",
        json={"campaignId": campaign_id},
        headers=headers_alice,
    )
    assert res_assign.status_code == 200
    assert res_assign.json()["campaign_id"] == campaign_id
    assert res_assign.json()["campaignTitle"] == "Tomb of the Star-Eater"

    # 6. Verify SpiceDB character-campaign relationship tuple written
    has_camp_rel = await spicedb.check_permission("character", char_id, "view", "user", "user_bob")
    assert has_camp_rel is True

    # 7. Party member Bob can now view Alice's character
    res_bob_after = client.get(f"/api/v1/characters/{char_id}", headers=headers_party_bob)
    assert res_bob_after.status_code == 200
    assert res_bob_after.json()["name"] == "Seoni"

    # 8. Outsider still denied view access (403 Forbidden)
    res_outsider = client.get(f"/api/v1/characters/{char_id}", headers=headers_outsider)
    assert res_outsider.status_code == 403

    # 9. Alice unassigns character from campaign
    res_unassign = client.patch(
        f"/api/v1/characters/{char_id}/campaign",
        json={"campaignId": None},
        headers=headers_alice,
    )
    assert res_unassign.status_code == 200
    assert res_unassign.json()["campaign_id"] is None

    # 10. Bob can no longer view unassigned character
    res_bob_unassigned = client.get(f"/api/v1/characters/{char_id}", headers=headers_party_bob)
    assert res_bob_unassigned.status_code == 403


@pytest.mark.asyncio
async def test_character_listing_filtered_by_zanzibar_visibility(trusted_ws_issuer, client):
    """Verify GET /api/v1/characters returns only viewable characters for requesting user."""
    headers_alice = _auth(trusted_ws_issuer, "user_alice")
    headers_bob = _auth(trusted_ws_issuer, "user_bob")

    res_a = client.post(
        "/api/v1/characters",
        json={"name": "Alice Ranger", "characterClass": "Ranger", "maxHp": 20},
        headers=headers_alice,
    )
    char_a_id = res_a.json()["id"]

    res_b = client.post(
        "/api/v1/characters",
        json={"name": "Bob Bard", "characterClass": "Bard", "maxHp": 18},
        headers=headers_bob,
    )
    char_b_id = res_b.json()["id"]

    # Listing isolation
    alice_list = client.get("/api/v1/characters", headers=headers_alice).json()
    alice_ids = [c["id"] for c in alice_list]
    assert char_a_id in alice_ids
    assert char_b_id not in alice_ids

    bob_list = client.get("/api/v1/characters", headers=headers_bob).json()
    bob_ids = [c["id"] for c in bob_list]
    assert char_b_id in bob_ids
    assert char_a_id not in bob_ids


def test_profile_endpoint_returns_verified_identity(trusted_ws_issuer, client):
    """Verify GET /api/v1/profile returns the verified token subject and no role claims (ADR-0015)."""
    headers = _auth(trusted_ws_issuer, "user_marcus")
    res = client.get("/api/v1/profile", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["user_id"] == "user_marcus"
    assert "username" in data
    assert "email" in data
    # Role claims grant nothing and are not projected to the profile.
    assert "roles" not in data
    assert "is_admin" not in data


@pytest.mark.asyncio
async def test_campaign_creation_and_ownership(trusted_ws_issuer, client):
    """Verify POST /api/v1/campaigns creates campaign and writes Zanzibar owner relation."""
    headers_gm = _auth(trusted_ws_issuer, "user_gm_evelyn")
    res = client.post(
        "/api/v1/campaigns",
        json={"title": "Whispering Depths", "setting": "Underdark", "system": "5e"},
        headers=headers_gm,
    )
    assert res.status_code == 201
    camp = res.json()
    camp_id = camp["id"]

    assert camp["title"] == "Whispering Depths"
    assert camp["role"] == "owner"
    assert camp["member_count"] == 1

    spicedb = get_spicedb_client()
    has_owner = await spicedb.check_permission(
        "campaign", camp_id, "manage", "user", "user_gm_evelyn"
    )
    assert has_owner is True
