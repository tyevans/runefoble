"""Blackbox TDD frontdoor test suite for Character Roster and Party Assignment UI.

Part of TASK-0211 / PRD-0023 / US-0064.
Governed by:
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0012: Design System Theming and Bauhaus Modernism
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 6: File length limit (< 500 lines, component < 260 lines)
- Hard Invariant 7: Blackbox TDD with frontdoor setup
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from character_sheet.main import app as character_app
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent
UI_DIR = REPO_ROOT / "services" / "character_sheet" / "ui"
ROSTER_DIR = UI_DIR / "src" / "roster"


@pytest.fixture
def client() -> TestClient:
    return TestClient(character_app)


# ---------------------------------------------------------------------------
# 1. Microfrontend Manifest & Package Structure Integrity
# ---------------------------------------------------------------------------


def test_character_roster_manifest_frontdoor(client: TestClient) -> None:
    """Verify character_sheet service advertises roster components via GET /ui/manifest."""
    response = client.get("/ui/manifest")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "character_sheet"
    assert data["package"] == "@runefoble/character-sheet-ui"
    assert "runefoble-character-roster" in data["components"]
    assert "runefoble-character-builder-modal" in data["components"]


def test_manifest_file_matches_advertised_manifest() -> None:
    """Verify services/character_sheet/ui/manifest.json contains roster components."""
    manifest_path = UI_DIR / "manifest.json"
    assert manifest_path.is_file(), f"{manifest_path} must exist"

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_data["service"] == "character_sheet"
    assert manifest_data["package"] == "@runefoble/character-sheet-ui"
    assert "runefoble-character-roster" in manifest_data["components"]
    assert "runefoble-character-builder-modal" in manifest_data["components"]


def test_character_roster_package_exports() -> None:
    """Verify UI package configuration, exports, and re-exports for roster."""
    pkg_json = json.loads((UI_DIR / "package.json").read_text(encoding="utf-8"))
    assert pkg_json["name"] == "@runefoble/character-sheet-ui"
    assert "./roster" in pkg_json["exports"]
    assert "./roster/runefoble-character-roster" in pkg_json["exports"]
    assert "./roster/runefoble-character-builder-modal" in pkg_json["exports"]

    roster_index = (ROSTER_DIR / "index.ts").read_text(encoding="utf-8")
    assert "runefoble-character-roster.ts" in roster_index
    assert "runefoble-character-builder-modal.ts" in roster_index


# ---------------------------------------------------------------------------
# 2. Component Contracts & UI Invariants
# ---------------------------------------------------------------------------


def test_character_roster_component_contracts() -> None:
    """Verify runefoble-character-roster fulfills specification requirements."""
    roster_file = ROSTER_DIR / "runefoble-character-roster.ts"
    assert roster_file.is_file()

    src = roster_file.read_text(encoding="utf-8")

    assert "@customElement('runefoble-character-roster')" in src
    assert "class RunefobleCharacterRoster" in src
    assert "characters" in src
    assert "campaigns" in src
    assert "activeFilter" in src
    assert "filteredList" in src

    # Quick action buttons
    assert "Inspect Sheet" in src
    assert "Assign to Campaign" in src
    assert "Delete" in src

    # CustomEvents dispatched
    assert "'inspect-character'" in src
    assert "'assign-campaign'" in src
    assert "'delete-character'" in src
    assert "'create-character'" in src

    # Modal dialogs
    assert "assign-dialog" in src
    assert "empty-roster" in src


def test_character_builder_modal_contracts() -> None:
    """Verify runefoble-character-builder-modal fulfills specification requirements."""
    builder_file = ROSTER_DIR / "runefoble-character-builder-modal.ts"
    assert builder_file.is_file()

    src = builder_file.read_text(encoding="utf-8")

    assert "@customElement('runefoble-character-builder-modal')" in src
    assert "class RunefobleCharacterBuilderModal" in src

    # Required form fields
    assert "name" in src
    assert "characterClass" in src
    assert "level" in src
    assert "maxHp" in src
    assert "armorClass" in src
    assert "speed" in src
    assert "abilityScores" in src
    assert "portraitUrl" in src

    # CustomEvents dispatched
    assert "'create-character'" in src
    assert "'builder-close'" in src


# ---------------------------------------------------------------------------
# 3. Design Tokens & Zero Hex Literals Invariant (ADR-0012)
# ---------------------------------------------------------------------------


def test_zero_hardcoded_hexes_in_roster_styles() -> None:
    """Verify roster styles consume tokens with zero hardcoded hex literals."""
    hex_pattern = re.compile(r"#[0-9a-fA-F]{3,8}")

    for style_file in [
        ROSTER_DIR / "runefoble-character-roster.styles.ts",
        ROSTER_DIR / "runefoble-character-builder-modal.styles.ts",
    ]:
        assert style_file.is_file()
        css_text = style_file.read_text(encoding="utf-8")
        matches = hex_pattern.findall(css_text)
        assert not matches, f"Found hardcoded hex literals in {style_file.name}: {matches}"

        for token in [
            "--rf-border-color",
            "--rf-shadow",
            "--rf-text-primary",
            "--rf-accent-primary",
        ]:
            assert token in css_text, f"Expected {token} in {style_file.name}"


# ---------------------------------------------------------------------------
# 4. File Length Limits (< 260 lines DoD, < 500 lines Hard Invariant 6)
# ---------------------------------------------------------------------------


def test_roster_files_line_counts() -> None:
    """Verify files comply with line count constraints (<260 lines for components, <500 total)."""
    roster_file = ROSTER_DIR / "runefoble-character-roster.ts"
    builder_file = ROSTER_DIR / "runefoble-character-builder-modal.ts"

    roster_lines = len(roster_file.read_text(encoding="utf-8").splitlines())
    builder_lines = len(builder_file.read_text(encoding="utf-8").splitlines())

    assert roster_lines < 260, (
        f"runefoble-character-roster.ts has {roster_lines} lines (must be < 260)"
    )
    assert builder_lines < 260, (
        f"runefoble-character-builder-modal.ts has {builder_lines} lines (must be < 260)"
    )

    for p in ROSTER_DIR.glob("*.ts"):
        line_count = len(p.read_text(encoding="utf-8").splitlines())
        assert line_count < 500, f"{p.name} exceeds 500 line invariant with {line_count} lines"


# ---------------------------------------------------------------------------
# 5. Storybook Stories
# ---------------------------------------------------------------------------


def test_roster_storybook_stories_exist() -> None:
    """Verify Storybook stories exist for roster and builder modal."""
    roster_stories = ROSTER_DIR / "runefoble-character-roster.stories.ts"
    assert roster_stories.is_file()
    r_content = roster_stories.read_text(encoding="utf-8")
    assert "PopulatedRoster" in r_content
    assert "EmptyRoster" in r_content
    assert "FilteredAssigned" in r_content
    assert "FilteredUnassigned" in r_content

    builder_stories = ROSTER_DIR / "runefoble-character-builder-modal.stories.ts"
    assert builder_stories.is_file()
    b_content = builder_stories.read_text(encoding="utf-8")
    assert "ModalOpen" in b_content
    assert "PrepopulatedModal" in b_content
    assert "ModalClosed" in b_content


# ---------------------------------------------------------------------------
# 6. Public Frontdoor Character Creation API
# ---------------------------------------------------------------------------


def test_create_character_public_api_frontdoor(client: TestClient) -> None:
    """Verify public POST /api/v1/characters endpoint handles character creation."""
    payload = {
        "name": "Valeros",
        "character_class": "Fighter",
        "max_hp": 45,
        "player_id": "usr-marcus",
        "personality_traits": ["brave", "protective"],
    }
    response = client.post("/api/v1/characters", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Valeros"
    assert data["character_class"] == "Fighter"
    assert data["max_hp"] == 45
    assert data["current_hp"] == 45
    assert data["player_id"] == "usr-marcus"
    assert "character_id" in data
