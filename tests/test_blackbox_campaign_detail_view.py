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

import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
SRC_DIR = FRONTEND_DIR / "src"
STYLES_DIR = SRC_DIR / "styles"
SERVICES_DIR = SRC_DIR / "services"
TESTS_DIR = FRONTEND_DIR / "test"

TEST_CAMPAIGN_DETAIL_TS = TESTS_DIR / "campaign-detail-view.test.ts"


@pytest.fixture
def client(game_session_upstream) -> Iterator[TestClient]:
    with TestClient(gateway_app) as gateway_client:
        yield gateway_client


# ---------------------------------------------------------------------------
# 1. Hard Invariant 6: File Length Constraints
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 2. Sub-View Disambiguation and Component Orchestration
# ---------------------------------------------------------------------------


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


def test_gateway_campaign_detail_and_patch_update_frontdoor(
    client: TestClient, trusted_ws_issuer
) -> None:
    """Verify campaign creation, retrieval, and PATCH update through gateway public frontdoor."""
    owner_headers = {"Authorization": f"Bearer {trusted_ws_issuer.mint('dm_alyssa')}"}

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
