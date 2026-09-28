"""Blackbox TDD frontdoor test suite for Unified Campaign Detail View Orchestration.

Part of TASK-0250 / PRD-0023 / US-0064 / US-0067.
Governed by:
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0007: Domain-Driven Design Architecture
- ADR-0012: Design System Theming and Bauhaus Modernism
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 6: File length limit (< 450 lines for App Shell, < 500 lines overall)
- Hard Invariant 7: Blackbox TDD with public frontdoors
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from gateway_api.campaign_store import campaign_store
from gateway_api.main import app as gateway_app

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
SRC_DIR = FRONTEND_DIR / "src"
STYLES_DIR = SRC_DIR / "styles"
SERVICES_DIR = SRC_DIR / "services"
TESTS_DIR = FRONTEND_DIR / "test"

APP_TS = SRC_DIR / "runefoble-app.ts"
APP_STYLES_TS = STYLES_DIR / "app-shell.styles.ts"
DATA_SERVICE_TS = SERVICES_DIR / "app-data-service.ts"
TEST_CAMPAIGN_DETAIL_TS = TESTS_DIR / "campaign-detail-view.test.ts"


@pytest.fixture
def client() -> TestClient:
    return TestClient(gateway_app)


@pytest.fixture(autouse=True)
def reset_store():
    campaign_store.reset()
    yield


# ---------------------------------------------------------------------------
# 1. Hard Invariant 6: File Length Constraints
# ---------------------------------------------------------------------------


def test_campaign_detail_file_length_invariants() -> None:
    """Verify runefoble-app.ts is strictly < 450 lines (and < 500) and supporting files comply."""
    assert APP_TS.is_file(), f"{APP_TS} must exist"
    app_lines = len(APP_TS.read_text(encoding="utf-8").splitlines())
    assert app_lines < 450, f"runefoble-app.ts has {app_lines} lines; must be < 450 lines (DoD 5)"
    assert app_lines < 250, (
        f"runefoble-app.ts has {app_lines} lines; must also satisfy < 250 baseline"
    )

    assert APP_STYLES_TS.is_file(), f"{APP_STYLES_TS} must exist"
    assert len(APP_STYLES_TS.read_text(encoding="utf-8").splitlines()) < 500

    assert DATA_SERVICE_TS.is_file(), f"{DATA_SERVICE_TS} must exist"
    assert len(DATA_SERVICE_TS.read_text(encoding="utf-8").splitlines()) < 500

    assert TEST_CAMPAIGN_DETAIL_TS.is_file(), f"{TEST_CAMPAIGN_DETAIL_TS} must exist"
    assert len(TEST_CAMPAIGN_DETAIL_TS.read_text(encoding="utf-8").splitlines()) < 500


# ---------------------------------------------------------------------------
# 2. Sub-View Disambiguation and Component Orchestration
# ---------------------------------------------------------------------------


def test_campaign_detail_subview_disambiguation_in_app_shell() -> None:
    """Verify runefoble-app.ts disambiguates #/campaigns/:id/characters and #/profile."""
    app_code = APP_TS.read_text(encoding="utf-8")

    # AppActiveView union includes new subviews
    assert "'campaign-characters'" in app_code
    assert "'profile'" in app_code

    # Disambiguation logic in getActiveView()
    assert "#/campaigns/:campaignId/characters" in app_code
    assert "#/profile" in app_code

    # Mounted components in campaign command center
    assert "runefoble-campaign-header" in app_code
    assert "runefoble-campaign-members" in app_code
    assert "runefoble-session-list" in app_code
    assert "runefoble-character-roster" in app_code

    # Header event handling and campaign updating
    assert "handleUpdateCampaign" in app_code
    assert "@update-campaign" in app_code
    assert "updateCampaign" in app_code


def test_tabbed_navigation_bar_and_bauhaus_tokens() -> None:
    """Verify tab bar renders four tabs and styles adhere to Bauhaus design tokens without hex literals."""
    app_code = APP_TS.read_text(encoding="utf-8")
    styles_code = APP_STYLES_TS.read_text(encoding="utf-8")

    # Tab labels
    assert "Overview & Sessions" in app_code
    assert "Party Characters" in app_code
    assert "Codex & Lore" in app_code
    assert "Chronicle & Stats" in app_code

    # Bauhaus tab styling classes
    assert ".campaign-hub-layout" in styles_code
    assert ".campaign-nav-tabs" in styles_code
    assert ".nav-tab" in styles_code
    assert ".nav-tab.active" in styles_code

    # Adherence to Bauhaus design tokens
    assert "--rf-border-color" in styles_code
    assert "--rf-accent-primary" in styles_code
    assert "--rf-bg-surface" in styles_code

    # No hardcoded hex color literals in CSS block
    hex_pattern = re.compile(r"#[0-9a-fA-F]{3,8}")
    css_match = re.search(r"css`([\s\S]*?)`", styles_code)
    assert css_match, "appShellStyles css block must exist"
    hexes = hex_pattern.findall(css_match.group(1))
    assert not hexes, f"Found hardcoded hex literals in appShellStyles: {hexes}"


def test_app_data_service_campaign_api_methods() -> None:
    """Verify AppDataService exports fetchCampaign and updateCampaign with proper PATCH wiring."""
    service_code = DATA_SERVICE_TS.read_text(encoding="utf-8")

    assert "fetchCampaign(" in service_code
    assert "updateCampaign(" in service_code
    assert "UpdateCampaignPayload" in service_code
    assert "PATCH" in service_code


# ---------------------------------------------------------------------------
# 3. Node.js TypeScript Test Suite Execution
# ---------------------------------------------------------------------------


def test_node_campaign_detail_view_suite_execution() -> None:
    """Execute the Node-based TypeScript campaign detail view test suite."""
    assert TEST_CAMPAIGN_DETAIL_TS.is_file(), f"{TEST_CAMPAIGN_DETAIL_TS} must exist"

    result = subprocess.run(
        [
            "node",
            "--experimental-strip-types",
            "--test",
            str(TEST_CAMPAIGN_DETAIL_TS.relative_to(REPO_ROOT)),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Node tests failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "Campaign Detail Sub-View Disambiguation (TASK-0250)" in result.stdout
    assert "Campaign Metadata Loading & Update Flow (TASK-0250)" in result.stdout
    assert "fail 0" in result.stdout


# ---------------------------------------------------------------------------
# 4. Gateway Frontdoor Blackbox Integration
# ---------------------------------------------------------------------------


def test_gateway_campaign_detail_and_patch_update_frontdoor(client: TestClient) -> None:
    """Verify campaign creation, retrieval, and PATCH update through gateway public frontdoor."""
    owner_headers = {"X-User-Id": "dm_alyssa"}

    create_res = client.post(
        "/api/v1/campaigns",
        json={
            "title": "Crown of the Sun King",
            "setting": "Solar Citadel",
            "system": "5e",
            "description": "High fantasy celestial exploration.",
        },
        headers=owner_headers,
    )
    assert create_res.status_code == 201
    campaign_id = create_res.json()["id"]

    # Fetch initial campaign details
    get_res = client.get(f"/api/v1/campaigns/{campaign_id}", headers=owner_headers)
    assert get_res.status_code == 200
    assert get_res.json()["title"] == "Crown of the Sun King"
    assert get_res.json()["setting"] == "Solar Citadel"

    # Update campaign details via PATCH frontdoor
    patch_res = client.patch(
        f"/api/v1/campaigns/{campaign_id}",
        json={
            "title": "Eclipse of the Sun King",
            "setting": "Ruined Solar Citadel",
            "description": "The golden spires fall to ancient shadows.",
        },
        headers=owner_headers,
    )
    assert patch_res.status_code == 200
    updated_data = patch_res.json()
    assert updated_data["title"] == "Eclipse of the Sun King"
    assert updated_data["setting"] == "Ruined Solar Citadel"
    assert updated_data["description"] == "The golden spires fall to ancient shadows."

    # Re-fetch to ensure persistence across frontdoor queries
    recheck_res = client.get(f"/api/v1/campaigns/{campaign_id}", headers=owner_headers)
    assert recheck_res.status_code == 200
    assert recheck_res.json()["title"] == "Eclipse of the Sun King"
