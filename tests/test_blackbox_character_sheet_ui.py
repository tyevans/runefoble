"""Blackbox TDD frontdoor test suite for Character Sheet UI Microfrontend.

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0007: API Gateway Architecture and Service Endpoints
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from character_sheet.main import app as character_app
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def client() -> TestClient:
    return TestClient(character_app)


# ---------------------------------------------------------------------------
# 1. Microfrontend Manifest & File Structure Integrity
# ---------------------------------------------------------------------------


def test_character_sheet_manifest_endpoint(client: TestClient) -> None:
    """Verify GET /ui/manifest frontdoor exposes correct microfrontend metadata."""
    resp = client.get("/ui/manifest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "character_sheet"
    assert data["package"] == "@runefoble/character-sheet-ui"
    assert data["version"] == "0.1.0"
    assert "runefoble-character-sheet" in data["components"]
    assert "runefoble-character-card" in data["components"]
    assert "runefoble-absentee-recap" in data["components"]
    assert "runefoble-stand-in-guardrails" in data["components"]
    assert "runefoble-character-sheet" in data["tags"]
    assert any("runefoble-character-sheet.styles" in s for s in data["styles"])
    assert any("index.ts" in sc for sc in data["scripts"])


def test_manifest_file_matches_advertised_manifest(client: TestClient) -> None:
    """Verify services/character_sheet/ui/manifest.json matches runtime advertising."""
    manifest_path = REPO_ROOT / "services/character_sheet/ui/manifest.json"
    assert manifest_path.is_file(), f"{manifest_path} must exist"

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    endpoint_data = client.get("/ui/manifest").json()

    assert manifest_data["service"] == endpoint_data["service"]
    assert manifest_data["package"] == endpoint_data["package"]
    assert manifest_data["components"] == endpoint_data["components"]
    assert manifest_data["tags"] == endpoint_data["tags"]


def test_typescript_element_source_and_custom_elements() -> None:
    """Verify UI package configuration, exports, and Custom Element decorators."""
    ui_dir = REPO_ROOT / "services/character_sheet/ui"

    pkg_json = json.loads((ui_dir / "package.json").read_text(encoding="utf-8"))
    assert pkg_json["name"] == "@runefoble/character-sheet-ui"
    assert "./runefoble-character-sheet" in pkg_json["exports"]
    assert "./runefoble-character-sheet.styles" in pkg_json["exports"]

    assert (ui_dir / "tsconfig.json").is_file()
    assert (ui_dir / "src/index.ts").is_file()

    comp_file = ui_dir / "src/runefoble-character-sheet.ts"
    assert comp_file.is_file()
    comp_src = comp_file.read_text(encoding="utf-8")
    assert "@customElement('runefoble-character-sheet')" in comp_src
    assert "class RunefobleCharacterSheet" in comp_src
    assert "encumbrance" in comp_src

    styles_file = ui_dir / "src/runefoble-character-sheet.styles.ts"
    assert styles_file.is_file()
    styles_src = styles_file.read_text(encoding="utf-8")
    assert "characterSheetStyles" in styles_src
    assert "--rf-border-width" in styles_src

    types_file = ui_dir / "src/runefoble-character-sheet.types.ts"
    assert types_file.is_file()
    types_src = types_file.read_text(encoding="utf-8")
    assert "KNOWN_CONDITION_DETAILS" in types_src
    assert "blinded" in types_src
    assert "drunk" in types_src

    templates_file = ui_dir / "src/runefoble-character-sheet.templates.ts"
    assert templates_file.is_file()


def test_storybook_stories_definition() -> None:
    """Verify Storybook stories include Healthy, Encumbered, Afflicted, and LeveledUpSpellcaster."""
    stories_file = (
        REPO_ROOT / "services/character_sheet/ui/src/runefoble-character-sheet.stories.ts"
    )
    assert stories_file.is_file()
    content = stories_file.read_text(encoding="utf-8")
    assert "Healthy" in content
    assert "Encumbered" in content
    assert "Afflicted" in content
    assert "LeveledUpSpellcaster" in content
    assert "runefoble-character-sheet" in content


def test_frontend_app_shell_forwarding_export() -> None:
    """Verify frontend/src/components/ re-exports runefoble-character-sheet per ADR-0013."""
    forwarding_file = REPO_ROOT / "frontend/src/components/runefoble-character-sheet.ts"
    assert forwarding_file.is_file()
    content = forwarding_file.read_text(encoding="utf-8")
    assert "@runefoble/character-sheet-ui" in content

    shell_index = REPO_ROOT / "frontend/src/index.ts"
    shell_src = shell_index.read_text(encoding="utf-8")
    assert "runefoble-character-sheet" in shell_src


# ---------------------------------------------------------------------------
# 2. REST Frontdoor Data Binding Integration
# ---------------------------------------------------------------------------


def test_rest_data_binding_character_full_lifecycle(client: TestClient) -> None:
    """Verify REST frontdoor endpoints deliver and mutate schemas bound to the microfrontend."""
    # 1. Create character via public frontdoor
    create_resp = client.post(
        "/api/v1/characters",
        json={
            "name": "Valeros the Bold",
            "character_class": "Fighter / Wizard",
            "max_hp": 40,
            "player_id": "player-marcus",
            "personality_traits": ["Daring", "Loyal"],
        },
    )
    assert create_resp.status_code == 200
    char_data = create_resp.json()
    char_id = char_data["character_id"]
    assert char_data["name"] == "Valeros the Bold"
    assert char_data["level"] == 1
    assert char_data["current_hp"] == 40
    assert char_data["max_hp"] == 40

    # 2. Query character data binding endpoint
    get_resp = client.get(f"/api/v1/characters/{char_id}")
    assert get_resp.status_code == 200
    sheet = get_resp.json()
    assert sheet["character_id"] == char_id
    assert isinstance(sheet["equipment"], dict)
    assert isinstance(sheet["inventory"], dict)
    assert isinstance(sheet["spell_slots"], dict)

    # 3. Add equipment and inventory items
    add_sword = client.post(
        f"/api/v1/characters/{char_id}/inventory/add",
        json={"item_id": "item-sword", "name": "Longsword +1", "quantity": 1, "weight_lbs": 3.0},
    )
    assert add_sword.status_code == 200
    assert "item-sword" in add_sword.json()["inventory"]

    add_shield = client.post(
        f"/api/v1/characters/{char_id}/inventory/add",
        json={"item_id": "item-shield", "name": "Steel Shield", "quantity": 1, "weight_lbs": 6.0},
    )
    assert add_shield.status_code == 200

    add_armor = client.post(
        f"/api/v1/characters/{char_id}/inventory/add",
        json={"item_id": "item-armor", "name": "Chain Mail", "quantity": 1, "weight_lbs": 55.0},
    )
    assert add_armor.status_code == 200

    # 4. Equip items into paper doll slots
    eq_main = client.post(
        f"/api/v1/characters/{char_id}/equipment",
        json={"slot": "main_hand", "item_name": "Longsword +1"},
    )
    assert eq_main.status_code == 200
    assert eq_main.json()["equipment"]["main_hand"] == "Longsword +1"

    eq_off = client.post(
        f"/api/v1/characters/{char_id}/equipment",
        json={"slot": "off_hand", "item_name": "Steel Shield"},
    )
    assert eq_off.status_code == 200
    assert eq_off.json()["equipment"]["off_hand"] == "Steel Shield"

    eq_armor = client.post(
        f"/api/v1/characters/{char_id}/equipment",
        json={"slot": "armor", "item_name": "Chain Mail"},
    )
    assert eq_armor.status_code == 200
    assert eq_armor.json()["equipment"]["armor"] == "Chain Mail"

    # 5. Apply condition and absence penalty
    cond_resp = client.post(
        f"/api/v1/characters/{char_id}/conditions",
        json={"condition": "blinded", "duration_rounds": 3, "source": "tactical"},
    )
    assert cond_resp.status_code == 200
    assert "blinded" in cond_resp.json()["conditions"]

    pen_resp = client.post(
        f"/api/v1/characters/{char_id}/penalties",
        json={
            "penalty_type": "drunk",
            "description": "Player missed session! Disadvantage on Dexterity.",
            "imposed_by": "the_watcher",
        },
    )
    assert pen_resp.status_code == 200
    assert "drunk" in pen_resp.json()["penalties"]

    # 6. Level up and prepare spell
    lvl_resp = client.post(f"/api/v1/characters/{char_id}/level-up")
    assert lvl_resp.status_code == 200
    assert lvl_resp.json()["level"] == 2

    prep_resp = client.post(
        f"/api/v1/characters/{char_id}/spells/prepare",
        json={"spell_name": "Magic Missile", "spell_level": 1},
    )
    assert prep_resp.status_code == 200
    assert "Magic Missile" in prep_resp.json()["prepared_spells"]

    # 7. Cast spell with slot expenditure
    cast_resp = client.post(
        f"/api/v1/characters/{char_id}/spells/cast",
        json={"spell_name": "Magic Missile", "slot_level": 1},
    )
    assert cast_resp.status_code == 200

    # 8. Verify final bound state contains all properties used by runefoble-character-sheet
    final_sheet = client.get(f"/api/v1/characters/{char_id}").json()
    assert final_sheet["name"] == "Valeros the Bold"
    assert final_sheet["level"] == 2
    assert final_sheet["equipment"]["main_hand"] == "Longsword +1"
    assert "item-sword" in final_sheet["inventory"]
    assert "blinded" in final_sheet["conditions"]
    assert "drunk" in final_sheet["penalties"]
    assert "Magic Missile" in final_sheet["prepared_spells"]


# ---------------------------------------------------------------------------
# 3. File Length & Hard Invariant 6 Enforcement
# ---------------------------------------------------------------------------


def test_file_length_invariants() -> None:
    """Verify that all files created for runefoble-character-sheet strictly obey Hard Invariant 6 (< 500 lines)."""
    monitored_files = [
        REPO_ROOT / "services/character_sheet/ui/src/runefoble-character-sheet.ts",
        REPO_ROOT / "services/character_sheet/ui/src/runefoble-character-sheet.templates.ts",
        REPO_ROOT / "services/character_sheet/ui/src/runefoble-character-sheet.styles.ts",
        REPO_ROOT / "services/character_sheet/ui/src/runefoble-character-sheet.types.ts",
        REPO_ROOT / "services/character_sheet/ui/src/runefoble-character-sheet.stories.ts",
        REPO_ROOT / "tests/test_blackbox_character_sheet_ui.py",
    ]

    for file_path in monitored_files:
        assert file_path.is_file(), f"{file_path} must exist"
        line_count = len(file_path.read_text(encoding="utf-8").splitlines())
        assert line_count < 500, (
            f"File {file_path.name} has {line_count} lines, exceeding the 500 line limit!"
        )
