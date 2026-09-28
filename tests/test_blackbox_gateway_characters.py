"""Blackbox frontdoor tests for Gateway Character Management and Zanzibar Authorization (TASK-0252).

Governing ADRs: ADR-0001 (SpiceDB Zanzibar), ADR-0005 (Zitadel OIDC), ADR-0007 (Domain-Driven Gateway).
Verifies:
1. Character creation and automatic SpiceDB Zanzibar ownership assignment.
2. Character listing filtered strictly by user ownership or Zanzibar view relation.
3. Character detail retrieval and 403 Forbidden rejection for unauthorized users.
4. Character campaign assignment and unassignment with Zanzibar edit permission.
5. Character deletion restricted exclusively to Zanzibar owner, removing relations.
6. CamelCase and snake_case dual compatibility for frontend Character Roster consumption.
"""

import pytest
from fastapi.testclient import TestClient
from gateway_api.auth import get_spicedb_client
from gateway_api.campaign_store import campaign_store
from gateway_api.character_store import character_store
from gateway_api.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_stores():
    """Reset character and campaign memory stores before each test."""
    character_store.reset(load_defaults=False)
    campaign_store.reset()
    yield


@pytest.mark.asyncio
async def test_character_creation_and_ownership():
    """Verify POST /api/v1/characters creates character and writes SpiceDB owner tuple."""
    headers_valeros = {"X-User-Id": "user_valeros"}

    payload = {
        "name": "Valeros of Korvosa",
        "characterClass": "Fighter",
        "subclass": "Battle Master",
        "level": 4,
        "currentHp": 38,
        "maxHp": 45,
        "armorClass": 18,
        "speed": 30,
        "portraitUrl": "/assets/portraits/fighter.svg",
    }

    res = client.post("/api/v1/characters", json=payload, headers=headers_valeros)
    assert res.status_code == 201
    data = res.json()

    assert data["name"] == "Valeros of Korvosa"
    assert data["character_class"] == "Fighter"
    assert data["characterClass"] == "Fighter"
    assert data["subclass"] == "Battle Master"
    assert data["level"] == 4
    assert data["current_hp"] == 38
    assert data["currentHp"] == 38
    assert data["max_hp"] == 45
    assert data["maxHp"] == 45
    assert data["armor_class"] == 18
    assert data["armorClass"] == 18
    assert data["speed"] == 30
    assert data["owner_id"] == "user_valeros"
    assert data["ownerId"] == "user_valeros"
    char_id = data["id"]

    # Verify SpiceDB has the owner relationship tuple
    spicedb = get_spicedb_client()
    has_owner = await spicedb.check_permission(
        "character", char_id, "owner", "user", "user_valeros"
    )
    assert has_owner is True

    # Owner has view permission
    has_view = await spicedb.check_permission("character", char_id, "view", "user", "user_valeros")
    assert has_view is True


@pytest.mark.asyncio
async def test_character_listing_isolation():
    """Verify GET /api/v1/characters lists only characters owned or viewable by the user."""
    headers_alice = {"X-User-Id": "user_alice"}
    headers_bob = {"X-User-Id": "user_bob"}

    # Alice creates a wizard
    res_a = client.post(
        "/api/v1/characters",
        json={"name": "Alice the Arcane", "characterClass": "Wizard", "level": 3, "maxHp": 20},
        headers=headers_alice,
    )
    assert res_a.status_code == 201
    char_a_id = res_a.json()["id"]

    # Bob creates a rogue
    res_b = client.post(
        "/api/v1/characters",
        json={"name": "Bob the Shadow", "characterClass": "Rogue", "level": 3, "maxHp": 22},
        headers=headers_bob,
    )
    assert res_b.status_code == 201
    char_b_id = res_b.json()["id"]

    # Alice lists characters -> only sees Alice's character
    alice_chars = client.get("/api/v1/characters", headers=headers_alice).json()
    alice_ids = [c["id"] for c in alice_chars]
    assert char_a_id in alice_ids
    assert char_b_id not in alice_ids

    # Bob lists characters -> only sees Bob's character
    bob_chars = client.get("/api/v1/characters", headers=headers_bob).json()
    bob_ids = [c["id"] for c in bob_chars]
    assert char_b_id in bob_ids
    assert char_a_id not in bob_ids


@pytest.mark.asyncio
async def test_character_detail_and_zanzibar_view_guard():
    """Verify GET /api/v1/characters/{id} returns details for owner and 403 for strangers."""
    headers_alice = {"X-User-Id": "user_alice"}
    headers_stranger = {"X-User-Id": "user_stranger"}

    res = client.post(
        "/api/v1/characters",
        json={"name": "Alice Guard", "characterClass": "Paladin", "level": 2, "maxHp": 24},
        headers=headers_alice,
    )
    char_id = res.json()["id"]

    # Alice (owner) can view details
    res_alice = client.get(f"/api/v1/characters/{char_id}", headers=headers_alice)
    assert res_alice.status_code == 200
    assert res_alice.json()["name"] == "Alice Guard"

    # Stranger without Zanzibar relation is denied access with 403
    res_denied = client.get(f"/api/v1/characters/{char_id}", headers=headers_stranger)
    assert res_denied.status_code == 403
    assert res_denied.json()["detail"]["error"] == "permission_denied"


@pytest.mark.asyncio
async def test_character_campaign_assignment_and_view_propagation():
    """Verify PATCH /api/v1/characters/{id}/campaign writes campaign tuple and propagates view."""
    headers_alice = {"X-User-Id": "user_alice"}
    headers_dm = {"X-User-Id": "dm_merlin"}
    headers_party_member = {"X-User-Id": "user_grognak"}
    headers_outsider = {"X-User-Id": "user_outsider"}

    # DM creates Campaign
    camp_res = client.post(
        "/api/v1/campaigns",
        json={"title": "Curse of Strahd", "setting": "Barovia"},
        headers=headers_dm,
    )
    campaign_id = camp_res.json()["id"]

    # Add Grognak as a player in the campaign
    await get_spicedb_client().write_relationship(
        "campaign", campaign_id, "player", "user", "user_grognak"
    )

    # Alice creates an unassigned character
    res = client.post(
        "/api/v1/characters",
        json={"name": "Alice Barovian", "characterClass": "Cleric", "level": 1, "maxHp": 12},
        headers=headers_alice,
    )
    char_id = res.json()["id"]

    # Before assignment: Grognak cannot view Alice's character
    res_grognak_before = client.get(f"/api/v1/characters/{char_id}", headers=headers_party_member)
    assert res_grognak_before.status_code == 403

    # Outsider cannot edit character or assign campaign (403 Forbidden)
    res_outsider_patch = client.patch(
        f"/api/v1/characters/{char_id}/campaign",
        json={"campaignId": campaign_id},
        headers=headers_outsider,
    )
    assert res_outsider_patch.status_code == 403

    # Alice (owner) assigns character to campaign
    res_patch = client.patch(
        f"/api/v1/characters/{char_id}/campaign",
        json={"campaignId": campaign_id},
        headers=headers_alice,
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["campaign_id"] == campaign_id
    assert res_patch.json()["campaignId"] == campaign_id
    assert res_patch.json()["campaignTitle"] == "Curse of Strahd"

    # After assignment: Campaign party member Grognak now has Zanzibar view permission!
    res_grognak_after = client.get(f"/api/v1/characters/{char_id}", headers=headers_party_member)
    assert res_grognak_after.status_code == 200
    assert res_grognak_after.json()["name"] == "Alice Barovian"

    # Outsider still has 403 Forbidden
    res_outsider_after = client.get(f"/api/v1/characters/{char_id}", headers=headers_outsider)
    assert res_outsider_after.status_code == 403

    # Unassign character from campaign
    res_unassign = client.patch(
        f"/api/v1/characters/{char_id}/campaign",
        json={"campaignId": None},
        headers=headers_alice,
    )
    assert res_unassign.status_code == 200
    assert res_unassign.json()["campaign_id"] is None

    # Grognak can no longer view unassigned character
    res_grognak_unassigned = client.get(
        f"/api/v1/characters/{char_id}", headers=headers_party_member
    )
    assert res_grognak_unassigned.status_code == 403


@pytest.mark.asyncio
async def test_character_deletion_owner_only():
    """Verify DELETE /api/v1/characters/{id} allows owner and blocks non-owners with 403."""
    headers_alice = {"X-User-Id": "user_alice"}
    headers_bob = {"X-User-Id": "user_bob"}

    res = client.post(
        "/api/v1/characters",
        json={"name": "Alice to Delete", "characterClass": "Bard", "level": 1, "maxHp": 10},
        headers=headers_alice,
    )
    char_id = res.json()["id"]

    # Non-owner Bob tries to delete Alice's character -> 403 Forbidden
    res_bob_delete = client.delete(f"/api/v1/characters/{char_id}", headers=headers_bob)
    assert res_bob_delete.status_code == 403
    assert res_bob_delete.json()["detail"]["error"] == "permission_denied"

    # Alice (owner) deletes her character
    res_alice_delete = client.delete(f"/api/v1/characters/{char_id}", headers=headers_alice)
    assert res_alice_delete.status_code == 200
    assert res_alice_delete.json()["status"] == "deleted"

    # Character is gone from store
    assert character_store.get_character(char_id) is None

    # Alice can no longer view deleted character
    res_after = client.get(f"/api/v1/characters/{char_id}", headers=headers_alice)
    assert res_after.status_code in (403, 404)


@pytest.mark.asyncio
async def test_default_characters_loaded_and_accessible():
    """Verify default seed characters are accessible to dev users."""
    character_store.load_defaults()

    # Valeros is owned by user-valeros
    res_valeros = client.get("/api/v1/characters", headers={"X-User-Id": "user-valeros"})
    assert res_valeros.status_code == 200
    ids_valeros = [c["id"] for c in res_valeros.json()]
    assert "char-valeros" in ids_valeros

    # Ezren is owned by dev-user-001
    res_ezren = client.get("/api/v1/characters", headers={"X-User-Id": "dev-user-001"})
    assert res_ezren.status_code == 200
    ids_ezren = [c["id"] for c in res_ezren.json()]
    assert "char-ezren" in ids_ezren


def test_file_length_invariants():
    """Verify all character gateway source files satisfy file length limits (<500 lines, target limits)."""
    import os

    targets = [
        ("gateway/api/src/gateway_api/routers/characters.py", 200),
        ("gateway/api/src/gateway_api/character_store.py", 250),
        ("gateway/api/src/gateway_api/character_models.py", 200),
        ("gateway/api/src/gateway_api/character_defaults.py", 100),
    ]

    for path, max_lines in targets:
        assert os.path.exists(path), f"File {path} does not exist"
        with open(path, encoding="utf-8") as f:
            lines = len(f.readlines())
        assert lines < max_lines, f"{path} has {lines} lines (exceeds target limit {max_lines})"
        assert lines < 500, f"{path} has {lines} lines (exceeds hard limit 500)"
