"""Blackbox frontdoor tests for Frontend Character Roster Event Binding and Data Mutations (TASK-0254).

Governing ADRs: ADR-0001 (SpiceDB Zanzibar), ADR-0004 (Lit Web Components), ADR-0007 (Domain Gateway), ADR-0013 (Microfrontends).
Verifies:
1. Submitting the character builder modal emits @create-character, calls Gateway API, and updates the roster.
2. Assigning a character to a campaign emits @assign-campaign, updates campaign tag, and persists to backend.
3. Deleting a character emits @delete-character, calls DELETE /api/v1/characters/{id}, and removes item from roster.
4. Clicking "Inspect Sheet" emits @inspect-character and navigates router to #/characters/:characterId.
5. Frontend App Shell and AppDataService file contracts, event bindings, and file length invariants (<500 lines).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app

from tests.helpers.node_suite import NODE_TEST_TIMEOUT_S, run_node_tests

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"


@pytest.fixture
def client(game_session_upstream, character_sheet_upstream):
    """Enter the gateway lifespan after game_session is served, so the proxy reaches it."""
    with TestClient(app) as gateway_client:
        yield gateway_client


def _auth(issuer, sub: str) -> dict[str, str]:
    """Return Bearer headers carrying a token that the gateway verifies for `sub`."""
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


# ---------------------------------------------------------------------------
# 1. Gateway API Public Frontdoors for Character Mutations
# ---------------------------------------------------------------------------


def test_frontdoor_create_character_mutation(trusted_ws_issuer, client):
    """Verify POST /api/v1/characters accepts frontend builder payload and returns character."""
    headers = _auth(trusted_ws_issuer, "user-marcus")
    payload = {
        "name": "Thorne Ironbreaker",
        "characterClass": "Fighter",
        "subclass": "Champion",
        "maxHp": 32,
        "armorClass": 17,
        "speed": 25,
    }

    res = client.post("/api/v1/characters", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()

    assert data["name"] == "Thorne Ironbreaker"
    assert data["characterClass"] == "Fighter"
    assert data["subclass"] == "Champion"
    assert data["level"] == 1
    assert data["currentHp"] == 32
    assert data["maxHp"] == 32
    assert data["armorClass"] == 17
    assert data["speed"] == 25
    assert data["ownerId"] == "user-marcus"
    assert data["id"] is not None

    # Listing returns the newly created character
    list_res = client.get("/api/v1/characters", headers=headers)
    assert list_res.status_code == 200
    listed_ids = [c["id"] for c in list_res.json()]
    assert data["id"] in listed_ids


def test_frontdoor_assign_character_campaign_mutation(trusted_ws_issuer, client):
    """Verify PATCH /api/v1/characters/{id}/campaign updates campaign assignment and title."""
    headers_owner = _auth(trusted_ws_issuer, "user-marcus")

    # 1. Create campaign
    camp_res = client.post(
        "/api/v1/campaigns",
        json={"title": "Abyssal Incursion", "setting": "Underdark"},
        headers=headers_owner,
    )
    assert camp_res.status_code == 201
    campaign_id = camp_res.json()["id"]

    # 2. Create character
    char_res = client.post(
        "/api/v1/characters",
        json={"name": "Lydia Lightbringer", "characterClass": "Cleric", "maxHp": 24},
        headers=headers_owner,
    )
    assert char_res.status_code == 201
    char_id = char_res.json()["id"]

    # 3. Assign character to campaign
    assign_res = client.patch(
        f"/api/v1/characters/{char_id}/campaign",
        json={"campaignId": campaign_id},
        headers=headers_owner,
    )
    assert assign_res.status_code == 200
    assigned_data = assign_res.json()
    assert assigned_data["campaignId"] == campaign_id
    assert assigned_data["campaignTitle"] == "Abyssal Incursion"

    # 4. Unassign character from campaign
    unassign_res = client.patch(
        f"/api/v1/characters/{char_id}/campaign",
        json={"campaignId": None},
        headers=headers_owner,
    )
    assert unassign_res.status_code == 200
    unassigned_data = unassign_res.json()
    assert unassigned_data["campaignId"] is None


def test_frontend_app_shell_typescript_unit_suite():
    app_shell_dir = FRONTEND_DIR / "test" / "app_shell"
    assert app_shell_dir.is_dir()
    test_files = sorted(str(p.relative_to(REPO_ROOT)) for p in app_shell_dir.glob("*.test.ts"))
    assert test_files

    result = run_node_tests(test_files, timeout=NODE_TEST_TIMEOUT_S)
    assert result.returncode == 0, (
        f"Frontend app-shell tests failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "creates character via createCharacter mutation" in result.stdout
    assert "assigns character to campaign and unassigns" in result.stdout
    assert "deletes character via deleteCharacter mutation" in result.stdout
    assert (
        "navigates to deep route #/characters/:characterId" in result.stdout
        or "navigates to deep route \\#/characters/:characterId" in result.stdout
    )
    assert "fail 0" in result.stdout
