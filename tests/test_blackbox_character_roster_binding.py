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

import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from gateway_api.campaign_store import campaign_store
from gateway_api.character_store import character_store
from gateway_api.main import app

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
APP_TS = FRONTEND_DIR / "src" / "runefoble-app.ts"
DATA_SERVICE_TS = FRONTEND_DIR / "src" / "services" / "app-data-service.ts"
APP_SHELL_STYLES_TS = FRONTEND_DIR / "src" / "styles" / "app-shell.styles.ts"
ROSTER_COMPONENT_TS = (
    REPO_ROOT
    / "services"
    / "character_sheet"
    / "ui"
    / "src"
    / "roster"
    / "runefoble-character-roster.ts"
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_stores():
    """Reset character and campaign memory stores before each test."""
    character_store.reset(load_defaults=False)
    campaign_store.reset()
    yield


# ---------------------------------------------------------------------------
# 1. Gateway API Public Frontdoors for Character Mutations
# ---------------------------------------------------------------------------


def test_frontdoor_create_character_mutation():
    """Verify POST /api/v1/characters accepts frontend builder payload and returns character."""
    headers = {"X-User-Id": "user-marcus"}
    payload = {
        "name": "Thorne Ironbreaker",
        "characterClass": "Fighter",
        "subclass": "Champion",
        "level": 3,
        "maxHp": 32,
        "armorClass": 17,
        "speed": 25,
        "portraitUrl": "/assets/portraits/fighter.svg",
    }

    res = client.post("/api/v1/characters", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()

    assert data["name"] == "Thorne Ironbreaker"
    assert data["characterClass"] == "Fighter"
    assert data["subclass"] == "Champion"
    assert data["level"] == 3
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


def test_frontdoor_assign_character_campaign_mutation():
    """Verify PATCH /api/v1/characters/{id}/campaign updates campaign assignment and title."""
    headers_owner = {"X-User-Id": "user-marcus"}

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


def test_frontdoor_delete_character_mutation():
    """Verify DELETE /api/v1/characters/{id} deletes character and removes from listing."""
    headers_owner = {"X-User-Id": "user-marcus"}

    # 1. Create character
    char_res = client.post(
        "/api/v1/characters",
        json={"name": "Disposable Hero", "characterClass": "Bard", "maxHp": 18},
        headers=headers_owner,
    )
    char_id = char_res.json()["id"]

    # 2. Verify exists in list
    assert char_id in [
        c["id"] for c in client.get("/api/v1/characters", headers=headers_owner).json()
    ]

    # 3. Delete character
    del_res = client.delete(f"/api/v1/characters/{char_id}", headers=headers_owner)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # 4. Verify removed from list
    assert char_id not in [
        c["id"] for c in client.get("/api/v1/characters", headers=headers_owner).json()
    ]


# ---------------------------------------------------------------------------
# 2. App Shell & AppDataService Frontend Contracts (TASK-0254)
# ---------------------------------------------------------------------------


def test_app_data_service_character_mutation_methods():
    """Verify AppDataService exports createCharacter, assignCharacterCampaign, and deleteCharacter."""
    content = DATA_SERVICE_TS.read_text(encoding="utf-8")

    # Mutation methods exist
    assert "createCharacter(payload: CreateCharacterPayload): Promise<CharacterItem>" in content
    assert (
        "assignCharacterCampaign(characterId: string, campaignId: string | null): Promise<void>"
        in content
    )
    assert "deleteCharacter(characterId: string): Promise<void>" in content

    # Hitting gateway endpoints
    assert "`${this.apiBase}/characters`" in content
    assert "method: 'POST'" in content
    assert "`${this.apiBase}/characters/${characterId}/campaign`" in content
    assert "method: 'PATCH'" in content
    assert "`${this.apiBase}/characters/${characterId}`" in content
    assert "method: 'DELETE'" in content


def test_app_shell_character_roster_event_binding():
    """Verify runefoble-app.ts binds all four actions dispatched by runefoble-character-roster."""
    content = APP_TS.read_text(encoding="utf-8")

    # Event listeners on runefoble-character-roster element
    assert "<runefoble-character-roster" in content
    assert "@create-character=${this.handleCreateCharacter}" in content
    assert "@assign-campaign=${this.handleAssignCampaign}" in content
    assert "@delete-character=${this.handleDeleteCharacter}" in content
    assert "@inspect-character=${this.handleInspectCharacter}" in content

    # Handler methods defined
    assert "handleCreateCharacter(e: CustomEvent" in content
    assert "handleAssignCampaign(e: CustomEvent" in content
    assert "handleDeleteCharacter(e: CustomEvent" in content
    assert "handleInspectCharacter(e: CustomEvent" in content

    # Inspect navigation to deep route #/characters/:characterId
    assert "router.navigate('#/characters/' + e.detail.characterId)" in content

    # Toast notification functionality
    assert "showToast(" in content
    assert "toastMessage" in content
    assert "toast-notification" in content


def test_roster_component_event_dispatches():
    """Verify runefoble-character-roster component emits all four expected events."""
    content = ROSTER_COMPONENT_TS.read_text(encoding="utf-8")

    assert "'create-character'" in content
    assert "'assign-campaign'" in content
    assert "'delete-character'" in content
    assert "'inspect-character'" in content


def test_toast_notification_bauhaus_tokens():
    """Verify toast notification styling in app-shell.styles.ts uses Bauhaus tokens with zero hexes."""
    import re

    content = APP_SHELL_STYLES_TS.read_text(encoding="utf-8")

    assert ".toast-notification" in content
    assert "var(--rf-bg-surface)" in content
    assert "var(--rf-text-primary)" in content
    assert "var(--rf-border-color)" in content
    assert "var(--rf-accent-primary)" in content
    assert "var(--rf-shadow)" in content

    # No hardcoded hexes
    hex_pattern = re.compile(r"#[0-9a-fA-F]{3,8}")
    assert not hex_pattern.findall(content)


# ---------------------------------------------------------------------------
# 3. File Length Limits (<500 lines Hard Invariant 6)
# ---------------------------------------------------------------------------


def test_file_length_invariants():
    """Verify all modified files strictly comply with Hard Invariant 6 (<500 lines)."""
    targets = [
        (APP_TS, 350),
        (DATA_SERVICE_TS, 450),
        (APP_SHELL_STYLES_TS, 150),
    ]

    for file_path, max_expected in targets:
        assert file_path.is_file(), f"{file_path} must exist"
        lines = len(file_path.read_text(encoding="utf-8").splitlines())
        assert lines < max_expected, (
            f"{file_path.name} has {lines} lines (expected < {max_expected})"
        )
        assert lines < 500, (
            f"{file_path.name} has {lines} lines (exceeds Hard Invariant 6 limit of 500)"
        )


# ---------------------------------------------------------------------------
# 4. Frontend TypeScript Test Execution
# ---------------------------------------------------------------------------


def test_frontend_app_shell_typescript_unit_suite():
    """Execute the Node-based TypeScript app-shell test suite including character roster bindings."""
    app_shell_test = FRONTEND_DIR / "test" / "app-shell.test.ts"
    assert app_shell_test.is_file()

    result = subprocess.run(
        [
            "node",
            "--experimental-strip-types",
            "--test",
            str(app_shell_test.relative_to(REPO_ROOT)),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Frontend app-shell tests failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "creates character via createCharacter mutation" in result.stdout
    assert "assigns character to campaign and unassigns" in result.stdout
    assert "deletes character via deleteCharacter mutation" in result.stdout
    assert "navigates to deep route #/characters/:characterId" in result.stdout
    assert "fail 0" in result.stdout
