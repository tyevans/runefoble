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

import re
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from gateway_api.auth import get_spicedb_client
from gateway_api.campaign_store import campaign_store
from gateway_api.character_store import character_store
from gateway_api.main import app

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
TS_TEST_FILE = FRONTEND_DIR / "test" / "character-management-and-profile.test.ts"
APP_SHELL_FILE = FRONTEND_DIR / "src" / "runefoble-app.ts"
ROUTER_FILE = FRONTEND_DIR / "src" / "router" / "router.ts"
APP_DATA_SERVICE_FILE = FRONTEND_DIR / "src" / "services" / "app-data-service.ts"
CHARACTER_CARD_FILE = (
    REPO_ROOT / "services" / "character_sheet" / "ui" / "src" / "runefoble-character-card.ts"
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_stores():
    """Reset in-memory character and campaign stores before each test."""
    character_store.reset(load_defaults=False)
    campaign_store.reset()
    yield


@pytest.mark.asyncio
async def test_character_crud_and_zanzibar_ownership():
    """Verify character creation, SpiceDB Zanzibar ownership relations, and owner-only deletion."""
    headers_owner = {"X-User-Id": "user_valeros"}
    headers_stranger = {"X-User-Id": "user_stranger"}

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

    # 1. Frontdoor POST /api/v1/characters
    res = client.post("/api/v1/characters", json=payload, headers=headers_owner)
    assert res.status_code == 201
    char_data = res.json()
    char_id = char_data["id"]

    assert char_data["name"] == "Valeros of Korvosa"
    assert char_data["character_class"] == "Fighter"
    assert char_data["characterClass"] == "Fighter"
    assert char_data["current_hp"] == 38
    assert char_data["max_hp"] == 45
    assert char_data["armor_class"] == 18
    assert char_data["owner_id"] == "user_valeros"

    # 2. Assert SpiceDB owner and permission tuples written
    spicedb = get_spicedb_client()
    assert (
        await spicedb.check_permission("character", char_id, "owner", "user", "user_valeros")
        is True
    )
    assert (
        await spicedb.check_permission("character", char_id, "view", "user", "user_valeros") is True
    )
    assert (
        await spicedb.check_permission("character", char_id, "edit", "user", "user_valeros") is True
    )

    # 3. Assert non-owner stranger cannot delete (403 Forbidden)
    res_stranger_del = client.delete(f"/api/v1/characters/{char_id}", headers=headers_stranger)
    assert res_stranger_del.status_code == 403
    assert res_stranger_del.json()["detail"]["error"] == "permission_denied"

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

    # 6. Assert owner can delete character
    res_owner_del = client.delete(f"/api/v1/characters/{char_id}", headers=headers_owner)
    assert res_owner_del.status_code == 200
    assert res_owner_del.json()["status"] == "deleted"

    # 7. Assert character is gone and inaccessible
    res_after = client.get(f"/api/v1/characters/{char_id}", headers=headers_owner)
    assert res_after.status_code in (403, 404)
    assert character_store.get_character(char_id) is None

    # 8. Assert SpiceDB owner relation is cleaned up
    assert (
        await spicedb.check_permission("character", char_id, "owner", "user", "user_valeros")
        is False
    )


@pytest.mark.asyncio
async def test_character_campaign_assignment():
    """Verify character campaign assignment writes campaign tuple and grants view to party members."""
    headers_alice = {"X-User-Id": "user_alice"}
    headers_party_bob = {"X-User-Id": "user_bob"}
    headers_outsider = {"X-User-Id": "user_outsider"}

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
        json={"name": "Seoni", "characterClass": "Sorcerer", "level": 3, "maxHp": 22},
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
async def test_character_listing_filtered_by_zanzibar_visibility():
    """Verify GET /api/v1/characters returns only viewable characters for requesting user."""
    headers_alice = {"X-User-Id": "user_alice"}
    headers_bob = {"X-User-Id": "user_bob"}

    res_a = client.post(
        "/api/v1/characters",
        json={"name": "Alice Ranger", "characterClass": "Ranger", "level": 2, "maxHp": 20},
        headers=headers_alice,
    )
    char_a_id = res_a.json()["id"]

    res_b = client.post(
        "/api/v1/characters",
        json={"name": "Bob Bard", "characterClass": "Bard", "level": 2, "maxHp": 18},
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


def test_profile_endpoint_claims_and_roles():
    """Verify GET /api/v1/profile returns authenticated Zitadel claims, user ID, and roles."""
    headers = {"X-User-Id": "user_marcus"}
    res = client.get("/api/v1/profile", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["user_id"] == "user_marcus"
    assert "roles" in data
    assert isinstance(data["roles"], list)
    assert "username" in data
    assert "email" in data


@pytest.mark.asyncio
async def test_campaign_creation_and_ownership():
    """Verify POST /api/v1/campaigns creates campaign and writes Zanzibar owner relation."""
    headers_gm = {"X-User-Id": "user_gm_evelyn"}
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
        "campaign", camp_id, "owner", "user", "user_gm_evelyn"
    )
    assert has_owner is True


def test_source_file_lengths_and_invariants():
    """Verify Hard Invariant 6: All files strictly satisfy length constraints (<500 lines)."""
    files_to_check = [
        (APP_SHELL_FILE, 450),
        (ROUTER_FILE, 300),
        (APP_DATA_SERVICE_FILE, 450),
        (CHARACTER_CARD_FILE, 500),
        (TS_TEST_FILE, 500),
        (Path(__file__), 500),
    ]

    for file_path, max_limit in files_to_check:
        assert file_path.is_file(), f"{file_path} must exist"
        lines = len(file_path.read_text(encoding="utf-8").splitlines())
        assert lines < max_limit, f"{file_path.name} has {lines} lines (expected < {max_limit})"
        assert lines < 500, f"{file_path.name} exceeds global limit of 500 lines"


def test_frontend_typescript_suite_execution():
    """Execute the Node-based TypeScript blackbox test suite and assert 100% pass."""
    assert TS_TEST_FILE.is_file(), f"Frontend test suite {TS_TEST_FILE} must exist"

    result = subprocess.run(
        [
            "node",
            "--experimental-strip-types",
            "--test",
            str(TS_TEST_FILE.relative_to(REPO_ROOT)),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Frontend blackbox suite failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )

    match = re.search(r"pass (\d+)", result.stdout)
    assert match is not None, f"Could not find pass count in output: {result.stdout}"
    assert int(match.group(1)) >= 7, f"Expected at least 7 passed tests, got {match.group(1)}"
    assert "fail 0" in result.stdout
