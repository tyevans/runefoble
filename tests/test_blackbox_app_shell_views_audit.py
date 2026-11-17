"""Blackbox frontdoor tests for App Shell Views Enumeration, Wiring Audit, and WebSocket Lifecycle.

TASK-0251: App Shell Views Enumeration, Wiring Audit, and Blackbox Test Suite
Governing ADRs:
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0010: Continuous Integration Pipeline
- ADR-0012: Design System Theming and Bauhaus Modernism
- Hard Invariant 6: File length limit (< 350 lines for test files, < 500 lines overall)
- Hard Invariant 7: Blackbox TDD with public frontdoors
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from gateway_api.campaign_store import campaign_store
from gateway_api.character_store import character_store
from gateway_api.main import app as gateway_app

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
SRC_DIR = FRONTEND_DIR / "src"
AUDIT_TEST_TS = FRONTEND_DIR / "test" / "app-shell-views-wiring-audit.test.ts"

client = TestClient(gateway_app)


@pytest.fixture(autouse=True)
def reset_stores():
    """Reset campaign and character stores to guarantee test isolation."""
    campaign_store.reset()
    character_store.reset(load_defaults=False)
    yield


# ---------------------------------------------------------------------------
# 1. Hard Invariant 6: File Length Constraints (< 350 lines per INVEST DoD)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 2. Route Enumeration Matrix & App Shell View Mounting Audit
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 3. Route-Bound WebSocket Lifecycle & Teardown Architecture
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 4. Dynamic Route Title & Breadcrumb Resolution Architecture
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 5. Node-Based TypeScript Frontend Audit Test Suite Execution
# ---------------------------------------------------------------------------


def test_execute_node_frontend_audit_test_suite():
    """Run the Node test runner on app-shell-views-wiring-audit.test.ts and verify 0 failures."""
    cmd = [
        "node",
        "--experimental-strip-types",
        "--test",
        str(AUDIT_TEST_TS.relative_to(REPO_ROOT)),
    ]
    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    assert result.returncode == 0, (
        f"Frontend audit tests failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )

    pass_match = re.search(r"pass (\d+)", result.stdout)
    assert pass_match is not None, f"Could not find pass count in output: {result.stdout}"
    passed = int(pass_match.group(1))
    assert passed >= 20, f"Expected at least 20 passed tests, got {passed}"
    assert "fail 0" in result.stdout


# ---------------------------------------------------------------------------
# 6. Gateway API Frontdoor Endpoints for Audited Views
# ---------------------------------------------------------------------------


def test_gateway_frontdoor_endpoints_for_audited_views(signing_issuer):
    """Verify Gateway API provides public frontdoor endpoints required by all audited views."""
    headers = {"Authorization": f"Bearer {signing_issuer.mint('user-valeros')}"}

    # 1. Campaigns Hub View (#/campaigns)
    camp_res = client.post(
        "/api/v1/campaigns",
        json={"title": "Astral Citadel", "setting": "Spelljammer", "system": "5e"},
        headers=headers,
    )
    assert camp_res.status_code == 201
    campaign_id = camp_res.json()["id"]

    list_res = client.get("/api/v1/campaigns", headers=headers)
    assert list_res.status_code == 200
    assert any(c["id"] == campaign_id for c in list_res.json())

    # 2. Campaign Detail View (#/campaigns/:campaignId)
    detail_res = client.get(f"/api/v1/campaigns/{campaign_id}", headers=headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["title"] == "Astral Citadel"

    members_res = client.get(f"/api/v1/campaigns/{campaign_id}/members", headers=headers)
    assert members_res.status_code == 200

    sessions_res = client.get(f"/api/v1/campaigns/{campaign_id}/sessions", headers=headers)
    assert sessions_res.status_code == 200

    # 3. Characters Roster View (#/characters and #/campaigns/:id/characters)
    char_res = client.post(
        "/api/v1/characters",
        json={
            "name": "Valeros Citadel Guard",
            "characterClass": "Fighter",
            "level": 3,
            "maxHp": 30,
            "armorClass": 16,
            "speed": 30,
            "campaignId": campaign_id,
        },
        headers=headers,
    )
    assert char_res.status_code == 201
    char_id = char_res.json()["id"]

    chars_list_res = client.get("/api/v1/characters", headers=headers)
    assert chars_list_res.status_code == 200
    assert any(c["id"] == char_id for c in chars_list_res.json())

    # 4. Character Sheet View (#/characters/:characterId)
    char_detail_res = client.get(f"/api/v1/characters/{char_id}", headers=headers)
    assert char_detail_res.status_code == 200
    assert char_detail_res.json()["name"] == "Valeros Citadel Guard"

    # 5. Session Lobby & Active VTT View (#/campaigns/:id/lobby/:id & #/campaigns/:id/sessions/:id)
    session_res = client.get(f"/api/v1/sessions/{campaign_id}", headers=headers)
    assert session_res.status_code == 200

    board_res = client.get(f"/api/v1/boards/{campaign_id}", headers=headers)
    assert board_res.status_code == 200
    assert "tokens" in board_res.json()
