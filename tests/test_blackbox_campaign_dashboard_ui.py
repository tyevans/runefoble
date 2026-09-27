"""Blackbox TDD frontdoor test suite for Campaign Dashboard and Creator UI.

Part of TASK-0209 / PRD-0023 / US-0063.
Governed by:
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0012: Design System Theming and Bauhaus Modernism
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 6: File length limit (< 500 lines)
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


def test_campaign_dashboard_manifest_frontdoor(client: TestClient) -> None:
    """Verify game_session service advertises campaign components via GET /ui/manifest."""
    response = client.get("/ui/manifest")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "game_session"
    assert data["package"] == "@runefoble/game-session-ui"
    assert data["version"] == "0.1.0"
    assert "runefoble-campaign-dashboard" in data["components"]
    assert "runefoble-campaign-creator" in data["components"]

    # Also test the routed alias /game_session/ui/manifest
    alias_res = client.get("/game_session/ui/manifest")
    assert alias_res.status_code == 200
    alias_data = alias_res.json()
    assert "runefoble-campaign-dashboard" in alias_data["components"]
    assert "runefoble-campaign-creator" in alias_data["components"]


def test_manifest_file_matches_advertised_manifest() -> None:
    """Verify services/game_session/ui/manifest.json matches runtime advertising."""
    manifest_path = UI_DIR / "manifest.json"
    assert manifest_path.is_file(), f"{manifest_path} must exist"

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_data["service"] == "game_session"
    assert manifest_data["package"] == "@runefoble/game-session-ui"
    assert "runefoble-campaign-dashboard" in manifest_data["components"]
    assert "runefoble-campaign-creator" in manifest_data["components"]


def test_campaign_typescript_exports() -> None:
    """Verify UI package configuration, exports, and re-exports in index.ts."""
    pkg_json = json.loads((UI_DIR / "package.json").read_text(encoding="utf-8"))
    assert pkg_json["name"] == "@runefoble/game-session-ui"
    assert "./campaigns" in pkg_json["exports"]
    assert "./campaigns/dashboard" in pkg_json["exports"]
    assert "./campaigns/creator" in pkg_json["exports"]

    index_ts = (UI_DIR / "src" / "index.ts").read_text(encoding="utf-8")
    assert "./campaigns/index.ts" in index_ts

    campaigns_index = (CAMPAIGNS_DIR / "index.ts").read_text(encoding="utf-8")
    assert "runefoble-campaign-dashboard.ts" in campaigns_index
    assert "runefoble-campaign-creator.ts" in campaigns_index
    assert "types.ts" in campaigns_index


# ---------------------------------------------------------------------------
# 2. Campaign Dashboard Component Contracts & UI Invariants
# ---------------------------------------------------------------------------


def test_campaign_dashboard_component_features() -> None:
    """Verify runefoble-campaign-dashboard fulfills specification requirements."""
    dashboard_file = CAMPAIGNS_DIR / "runefoble-campaign-dashboard.ts"
    assert dashboard_file.is_file()

    src = dashboard_file.read_text(encoding="utf-8")

    # Custom element registration
    assert "@customElement('runefoble-campaign-dashboard')" in src
    assert "class RunefobleCampaignDashboard" in src

    # Responsive grid and Bauhaus card rendering
    assert "campaigns-grid" in src
    assert "campaign-card" in src

    # Title, description, DM name, player count
    assert "card-title" in src
    assert "card-desc" in src
    assert "dm-info" in src
    assert "player-info" in src

    # Active session badge ("● Session Live")
    assert "● Session Live" in src
    assert "badge-live" in src

    # Role filtering ("All", "DMing", "Playing")
    assert "handleFilterChange" in src
    assert "'all'" in src
    assert "'dming'" in src
    assert "'playing'" in src

    # Text search
    assert "searchQuery" in src
    assert "handleSearchInput" in src

    # Events dispatched
    assert "'select-campaign'" in src
    assert "'open-creator'" in src
    assert "'create-campaign'" in src

    # Empty state
    assert "empty-state" in src


# ---------------------------------------------------------------------------
# 3. Campaign Creator Component Contracts & UI Invariants
# ---------------------------------------------------------------------------


def test_campaign_creator_component_features() -> None:
    """Verify runefoble-campaign-creator fulfills specification requirements."""
    creator_file = CAMPAIGNS_DIR / "runefoble-campaign-creator.ts"
    assert creator_file.is_file()

    src = creator_file.read_text(encoding="utf-8")

    # Custom element registration
    assert "@customElement('runefoble-campaign-creator')" in src
    assert "class RunefobleCampaignCreator" in src

    # Modal form fields: title, setting synopsis, ruleset selection, cover art URL
    assert "campaign-title" in src
    assert "campaign-setting" in src
    assert "campaign-ruleset" in src
    assert "campaign-cover" in src
    assert "campaign-description" in src

    # Ruleset options (e.g. SRD 5e, pf2e, etc.)
    assert "SRD 5e (Fifth Edition)" in src

    # Dispatches create-campaign event
    assert "'create-campaign'" in src
    assert "handleSubmit" in src

    # Dispatches close and cancel events
    assert "'close'" in src
    assert "'cancel'" in src
    assert "closeModal" in src

    # Form validation for required title
    assert "Campaign title is required." in src


# ---------------------------------------------------------------------------
# 4. Design Tokens & Zero Hex Literals Invariant (ADR-0012)
# ---------------------------------------------------------------------------


def test_zero_hardcoded_hexes_in_campaign_styles() -> None:
    """Verify campaign styles consume --rf-* tokens with zero hardcoded hex literals."""
    hex_pattern = re.compile(r"#[0-9a-fA-F]{3,8}")

    dashboard_styles_file = CAMPAIGNS_DIR / "runefoble-campaign-dashboard.styles.ts"
    creator_styles_file = CAMPAIGNS_DIR / "runefoble-campaign-creator.styles.ts"

    assert dashboard_styles_file.is_file()
    assert creator_styles_file.is_file()

    dash_css = dashboard_styles_file.read_text(encoding="utf-8")
    creator_css = creator_styles_file.read_text(encoding="utf-8")

    assert not hex_pattern.findall(dash_css), "Found hardcoded hex in dashboard styles"
    assert not hex_pattern.findall(creator_css), "Found hardcoded hex in creator styles"

    # Consumes Bauhaus tokens
    for token in ["--rf-border-color", "--rf-shadow", "--rf-text-primary"]:
        assert token in dash_css, f"Expected {token} in dashboard styles"
        assert token in creator_css, f"Expected {token} in creator styles"


# ---------------------------------------------------------------------------
# 5. File Length Limits (< 280 lines per DoD, < 500 lines Hard Invariant 6)
# ---------------------------------------------------------------------------


def test_campaign_files_line_counts() -> None:
    """Verify files comply with line count constraints (<280 lines for dashboard, <240 lines for creator)."""
    dashboard_file = CAMPAIGNS_DIR / "runefoble-campaign-dashboard.ts"
    creator_file = CAMPAIGNS_DIR / "runefoble-campaign-creator.ts"

    dashboard_lines = len(dashboard_file.read_text(encoding="utf-8").splitlines())
    creator_lines = len(creator_file.read_text(encoding="utf-8").splitlines())

    assert dashboard_lines < 280, (
        f"runefoble-campaign-dashboard.ts has {dashboard_lines} lines (must be < 280)"
    )
    assert creator_lines < 240, (
        f"runefoble-campaign-creator.ts has {creator_lines} lines (must be < 240)"
    )

    for p in CAMPAIGNS_DIR.glob("*.ts"):
        line_count = len(p.read_text(encoding="utf-8").splitlines())
        assert line_count < 500, f"{p.name} exceeds 500 line invariant with {line_count} lines"


# ---------------------------------------------------------------------------
# 6. Storybook Stories
# ---------------------------------------------------------------------------


def test_campaign_storybook_stories_exist() -> None:
    """Verify Storybook stories exist for dashboard and creator with required states."""
    dash_stories = CAMPAIGNS_DIR / "runefoble-campaign-dashboard.stories.ts"
    creator_stories = CAMPAIGNS_DIR / "runefoble-campaign-creator.stories.ts"

    assert dash_stories.is_file()
    assert creator_stories.is_file()

    dash_content = dash_stories.read_text(encoding="utf-8")
    assert "PopulatedWithMixedRoles" in dash_content
    assert "EmptyDashboard" in dash_content
    assert "FilteredDMingOnly" in dash_content
    assert "FilteredPlayingOnly" in dash_content

    creator_content = creator_stories.read_text(encoding="utf-8")
    assert "DefaultOpen" in creator_content
    assert "EmptyForm" in creator_content
    assert "WithValidationError" in creator_content
    assert "SubmittingState" in creator_content
