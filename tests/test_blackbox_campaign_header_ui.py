"""Blackbox TDD frontdoor test suite for Campaign Hero Header and Metadata UI.

Part of TASK-0248 / PRD-0023 / US-0067.
Governed by:
- ADR-0001: SpiceDB Zanzibar Object Authorization
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0012: Design System Theming and Bauhaus Modernism
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 6: File length limit (< 500 lines, component < 250 lines)
- Hard Invariant 7: Blackbox TDD with frontdoor setup
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from game_session.main import app as session_app

REPO_ROOT = Path(__file__).resolve().parent.parent
UI_DIR = REPO_ROOT / "services" / "game_session" / "ui"
CAMPAIGNS_DIR = UI_DIR / "src" / "campaigns"


@pytest.fixture
def client() -> TestClient:
    return TestClient(session_app)


# ---------------------------------------------------------------------------
# 1. Microfrontend Manifest & Package Structure Integrity
# ---------------------------------------------------------------------------


def test_campaign_header_manifest_frontdoor(client: TestClient) -> None:
    """Verify game_session service advertises runefoble-campaign-header via GET /ui/manifest."""
    response = client.get("/ui/manifest")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "game_session"
    assert data["package"] == "@runefoble/game-session-ui"
    assert "runefoble-campaign-header" in data["components"]

    alias_res = client.get("/game_session/ui/manifest")
    assert alias_res.status_code == 200
    alias_data = alias_res.json()
    assert "runefoble-campaign-header" in alias_data["components"]


def test_manifest_file_matches_advertised_manifest() -> None:
    """Verify services/game_session/ui/manifest.json contains runefoble-campaign-header."""
    manifest_path = UI_DIR / "manifest.json"
    assert manifest_path.is_file(), f"{manifest_path} must exist"

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_data["service"] == "game_session"
    assert manifest_data["package"] == "@runefoble/game-session-ui"
    assert "runefoble-campaign-header" in manifest_data["components"]


def test_campaign_header_package_exports() -> None:
    """Verify UI package configuration, exports, and re-exports for campaign header."""
    pkg_json = json.loads((UI_DIR / "package.json").read_text(encoding="utf-8"))
    assert pkg_json["name"] == "@runefoble/game-session-ui"
    assert "./campaigns/header" in pkg_json["exports"]
    assert "./campaigns/header.styles" in pkg_json["exports"]

    campaigns_index = (CAMPAIGNS_DIR / "index.ts").read_text(encoding="utf-8")
    assert "runefoble-campaign-header.ts" in campaigns_index
    assert "runefoble-campaign-header.styles.ts" in campaigns_index


# ---------------------------------------------------------------------------
# 2. Campaign Header Component Contracts & UI Invariants
# ---------------------------------------------------------------------------


def test_campaign_header_component_contracts() -> None:
    """Verify runefoble-campaign-header fulfills TASK-0248 requirements."""
    header_file = CAMPAIGNS_DIR / "runefoble-campaign-header.ts"
    assert header_file.is_file()

    src = header_file.read_text(encoding="utf-8")

    # Custom element registration and class
    assert "@customElement('runefoble-campaign-header')" in src
    assert "class RunefobleCampaignHeader" in src

    # Properties
    assert "campaign" in src
    assert "canManage" in src
    assert "currentUserId" in src

    # Hero banner and Bauhaus fallback pattern
    assert "hero-banner" in src
    assert "cover-image" in src
    assert "hero-banner-fallback" in src
    assert "geometric-pattern" in src

    # Metadata badges: Ruleset System, Setting Name, Active Status pill, and DM avatar/username
    assert "meta-badges-row" in src
    assert "badge-system" in src
    assert "badge-setting" in src
    assert "badge-status" in src
    assert "badge-dm-profile" in src
    assert "dm-avatar" in src
    assert "dm-name" in src

    # Campaign title & narrative description
    assert "campaign-title" in src
    assert "campaign-description" in src

    # Action row: Edit Campaign button visible when canManage
    assert "btn-edit-campaign" in src
    assert "Edit Campaign" in src

    # Edit Campaign modal dialog and form fields
    assert "modal-backdrop" in src
    assert "edit-campaign-title" in src
    assert "edit-campaign-setting" in src
    assert "edit-campaign-system" in src
    assert "edit-campaign-cover" in src
    assert "edit-campaign-description" in src

    # Dispatches 'update-campaign' custom event
    assert "'update-campaign'" in src


def test_campaign_header_types_and_helpers() -> None:
    """Verify types.ts defines UpdateCampaignPayload and formatRulesetSystem helper."""
    types_file = CAMPAIGNS_DIR / "types.ts"
    assert types_file.is_file()

    src = types_file.read_text(encoding="utf-8")
    assert "interface UpdateCampaignPayload" in src
    assert "function formatRulesetSystem" in src


# ---------------------------------------------------------------------------
# 3. Design Tokens & Zero Hex Literals Invariant (ADR-0012)
# ---------------------------------------------------------------------------


def test_zero_hardcoded_hexes_in_campaign_header_styles() -> None:
    """Verify campaign header styles consume --rf-* tokens with zero hardcoded hex literals."""
    hex_pattern = re.compile(r"#[0-9a-fA-F]{3,8}")

    styles_file = CAMPAIGNS_DIR / "runefoble-campaign-header.styles.ts"
    assert styles_file.is_file()

    css_text = styles_file.read_text(encoding="utf-8")
    matches = hex_pattern.findall(css_text)
    assert not matches, f"Found hardcoded hex literals in campaign header styles: {matches}"

    # Consumes Bauhaus tokens
    for token in [
        "--rf-border-color",
        "--rf-shadow",
        "--rf-text-primary",
        "--rf-accent-primary",
        "--rf-accent-secondary",
        "--rf-accent-tertiary",
    ]:
        assert token in css_text, f"Expected {token} in campaign header styles"


# ---------------------------------------------------------------------------
# 4. File Length Limits (< 250 lines per DoD, < 500 lines Hard Invariant 6)
# ---------------------------------------------------------------------------


def test_campaign_header_files_line_counts() -> None:
    """Verify files comply with line count constraints (<250 lines for component, <500 total)."""
    header_file = CAMPAIGNS_DIR / "runefoble-campaign-header.ts"
    styles_file = CAMPAIGNS_DIR / "runefoble-campaign-header.styles.ts"

    header_lines = len(header_file.read_text(encoding="utf-8").splitlines())
    styles_lines = len(styles_file.read_text(encoding="utf-8").splitlines())

    assert header_lines < 250, (
        f"runefoble-campaign-header.ts has {header_lines} lines (must be < 250)"
    )
    assert styles_lines < 500, (
        f"runefoble-campaign-header.styles.ts has {styles_lines} lines (must be < 500)"
    )

    for p in CAMPAIGNS_DIR.glob("*.ts"):
        line_count = len(p.read_text(encoding="utf-8").splitlines())
        assert line_count < 500, f"{p.name} exceeds 500 line invariant with {line_count} lines"


# ---------------------------------------------------------------------------
# 5. Storybook Stories
# ---------------------------------------------------------------------------


def test_campaign_header_storybook_stories_exist() -> None:
    """Verify Storybook stories exist for campaign header covering required states."""
    stories_file = CAMPAIGNS_DIR / "runefoble-campaign-header.stories.ts"
    assert stories_file.is_file()

    content = stories_file.read_text(encoding="utf-8")
    assert "GameMasterView" in content
    assert "PlayerView" in content
    assert "MinimalMetadata" in content
