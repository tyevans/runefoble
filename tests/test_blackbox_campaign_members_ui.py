"""Blackbox TDD frontdoor test suite for Campaign Members & Zanzibar Role Manager UI.

Part of TASK-0210 / PRD-0023 / US-0063.
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


def test_campaign_members_manifest_frontdoor(client: TestClient) -> None:
    """Verify game_session service advertises runefoble-campaign-members via GET /ui/manifest."""
    response = client.get("/ui/manifest")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "game_session"
    assert data["package"] == "@runefoble/game-session-ui"
    assert "runefoble-campaign-members" in data["components"]

    alias_res = client.get("/game_session/ui/manifest")
    assert alias_res.status_code == 200
    alias_data = alias_res.json()
    assert "runefoble-campaign-members" in alias_data["components"]


def test_manifest_file_matches_advertised_manifest() -> None:
    """Verify services/game_session/ui/manifest.json contains runefoble-campaign-members."""
    manifest_path = UI_DIR / "manifest.json"
    assert manifest_path.is_file(), f"{manifest_path} must exist"

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_data["service"] == "game_session"
    assert manifest_data["package"] == "@runefoble/game-session-ui"
    assert "runefoble-campaign-members" in manifest_data["components"]


def test_campaign_members_package_exports() -> None:
    """Verify UI package configuration, exports, and re-exports for campaign members."""
    pkg_json = json.loads((UI_DIR / "package.json").read_text(encoding="utf-8"))
    assert pkg_json["name"] == "@runefoble/game-session-ui"
    assert "./campaigns/members" in pkg_json["exports"]
    assert "./campaigns/members.styles" in pkg_json["exports"]

    campaigns_index = (CAMPAIGNS_DIR / "index.ts").read_text(encoding="utf-8")
    assert "runefoble-campaign-members.ts" in campaigns_index
    assert "runefoble-campaign-members.styles.ts" in campaigns_index


# ---------------------------------------------------------------------------
# 2. Campaign Members Component Contracts & UI Invariants
# ---------------------------------------------------------------------------


def test_campaign_members_component_contracts() -> None:
    """Verify runefoble-campaign-members fulfills specification requirements."""
    members_file = CAMPAIGNS_DIR / "runefoble-campaign-members.ts"
    assert members_file.is_file()

    src = members_file.read_text(encoding="utf-8")

    # Custom element registration and class
    assert "@customElement('runefoble-campaign-members')" in src
    assert "class RunefobleCampaignMembers" in src

    # Properties
    assert "campaignId" in src
    assert "campaignTitle" in src
    assert "members" in src
    assert "canManage" in src
    assert "isGm" in src
    assert "inviteUrl" in src
    assert "inviteToken" in src

    # Roster listing & profile elements
    assert "member-item" in src
    assert "renderAvatar" in src
    assert "character-tag" in src
    assert "user-id-tag" in src

    # Zanzibar role selection and badges
    assert "role-select" in src
    assert "dungeon_master" in src
    assert "player" in src
    assert "spectator" in src
    assert "badge-role" in src
    assert "'assign-role'" in src

    # Member removal and confirmation modal
    assert "btn-remove" in src
    assert "confirmRemove" in src
    assert "'remove-member'" in src
    assert "modal-backdrop" in src
    assert "Confirm Remove" in src

    # Invite generator and copyable share link
    assert "btn-invite" in src
    assert "openInviteModal" in src
    assert "closeInviteModal" in src
    assert "'create-invite'" in src
    assert "copyInviteLink" in src
    assert "'copy-invite-link'" in src
    assert "invite-link-input" in src
    assert "copied-badge" in src

    # Empty roster state
    assert "empty-state" in src


# ---------------------------------------------------------------------------
# 3. Design Tokens & Zero Hex Literals Invariant (ADR-0012)
# ---------------------------------------------------------------------------


def test_zero_hardcoded_hexes_in_campaign_members_styles() -> None:
    """Verify campaign members styles consume --rf-* tokens with zero hardcoded hex literals."""
    hex_pattern = re.compile(r"#[0-9a-fA-F]{3,8}")

    styles_file = CAMPAIGNS_DIR / "runefoble-campaign-members.styles.ts"
    assert styles_file.is_file()

    css_text = styles_file.read_text(encoding="utf-8")
    styles_sub_dir = CAMPAIGNS_DIR / "styles"
    if styles_sub_dir.is_dir():
        for sub_file in styles_sub_dir.glob("*.styles.ts"):
            css_text += "\n" + sub_file.read_text(encoding="utf-8")

    matches = hex_pattern.findall(css_text)
    assert not matches, f"Found hardcoded hex literals in campaign members styles: {matches}"

    # Consumes Bauhaus tokens
    for token in ["--rf-border-color", "--rf-shadow", "--rf-text-primary", "--rf-accent-primary"]:
        assert token in css_text, f"Expected {token} in campaign members styles"


# ---------------------------------------------------------------------------
# 4. File Length Limits (< 250 lines per DoD, < 500 lines Hard Invariant 6)
# ---------------------------------------------------------------------------


def test_campaign_members_files_line_counts() -> None:
    """Verify files comply with line count constraints (<250 lines for component, <500 total)."""
    members_file = CAMPAIGNS_DIR / "runefoble-campaign-members.ts"
    styles_file = CAMPAIGNS_DIR / "runefoble-campaign-members.styles.ts"

    members_lines = len(members_file.read_text(encoding="utf-8").splitlines())
    styles_lines = len(styles_file.read_text(encoding="utf-8").splitlines())

    assert members_lines < 250, (
        f"runefoble-campaign-members.ts has {members_lines} lines (must be < 250)"
    )
    assert styles_lines < 500, (
        f"runefoble-campaign-members.styles.ts has {styles_lines} lines (must be < 500)"
    )

    for p in CAMPAIGNS_DIR.glob("*.ts"):
        line_count = len(p.read_text(encoding="utf-8").splitlines())
        assert line_count < 500, f"{p.name} exceeds 500 line invariant with {line_count} lines"


# ---------------------------------------------------------------------------
# 5. Storybook Stories
# ---------------------------------------------------------------------------


def test_campaign_members_storybook_stories_exist() -> None:
    """Verify Storybook stories exist for campaign members covering GM and player views."""
    stories_file = CAMPAIGNS_DIR / "runefoble-campaign-members.stories.ts"
    assert stories_file.is_file()

    content = stories_file.read_text(encoding="utf-8")
    assert "GmManagementMode" in content
    assert "PlayerViewOnlyMode" in content
    assert "EmptyRoster" in content
    assert "CustomInviteLink" in content
