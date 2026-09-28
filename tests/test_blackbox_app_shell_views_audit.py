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
ROUTER_TS = SRC_DIR / "router" / "router.ts"
APP_TS = SRC_DIR / "runefoble-app.ts"
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


def test_audit_file_length_invariants():
    """Verify all audit files and modified components strictly satisfy line count constraints."""
    assert AUDIT_TEST_TS.is_file(), f"{AUDIT_TEST_TS} must exist"
    audit_lines = len(AUDIT_TEST_TS.read_text(encoding="utf-8").splitlines())
    assert audit_lines < 350, f"audit test has {audit_lines} lines; must be < 350 lines (DoD)"
    assert audit_lines < 500, f"audit test exceeds global 500 line limit: {audit_lines}"

    this_file = Path(__file__)
    py_lines = len(this_file.read_text(encoding="utf-8").splitlines())
    assert py_lines < 350, f"{this_file.name} has {py_lines} lines; must be < 350 lines (DoD)"
    assert py_lines < 500, f"{this_file.name} exceeds global 500 line limit: {py_lines}"

    assert APP_TS.is_file(), f"{APP_TS} must exist"
    app_lines = len(APP_TS.read_text(encoding="utf-8").splitlines())
    assert app_lines < 250, f"runefoble-app.ts has {app_lines} lines; must be < 250 baseline"

    assert ROUTER_TS.is_file(), f"{ROUTER_TS} must exist"
    router_lines = len(ROUTER_TS.read_text(encoding="utf-8").splitlines())
    assert router_lines < 250, f"router.ts has {router_lines} lines; must be < 250 baseline"


# ---------------------------------------------------------------------------
# 2. Route Enumeration Matrix & App Shell View Mounting Audit
# ---------------------------------------------------------------------------


def test_app_shell_views_route_enumeration_and_mounting():
    """Verify runefoble-app.ts enumerates all standard routes and mounts dedicated components."""
    app_code = APP_TS.read_text(encoding="utf-8")

    # AppActiveView union includes all nine standard views plus character-sheet
    expected_views = [
        "'login'",
        "'campaigns'",
        "'campaign-detail'",
        "'campaign-characters'",
        "'characters'",
        "'character-sheet'",
        "'session-lobby'",
        "'session-active'",
        "'profile'",
    ]
    for view in expected_views:
        assert view in app_code, f"View {view} must be declared in AppActiveView union"

    # Dedicated components mounted by view
    expected_components = [
        "runefoble-auth-modal",
        "runefoble-campaign-dashboard",
        "runefoble-campaign-header",
        "runefoble-campaign-members",
        "runefoble-session-list",
        "runefoble-character-roster",
        "runefoble-session-lobby",
        "runefoble-board",
        "runefoble-character-card",
        "runefoble-watcher-feed",
        "runefoble-voice-controls",
        "runefoble-user-profile",
        "runefoble-character-sheet",
    ]
    for comp in expected_components:
        assert comp in app_code, (
            f"Component {comp} must be imported and mounted in runefoble-app.ts"
        )


def test_app_shell_route_collision_prevention():
    """Verify getActiveView() prevents route collisions across nested and ambiguous paths."""
    app_code = APP_TS.read_text(encoding="utf-8")

    # #/profile disambiguation from #/campaigns
    assert "pat === '#/profile' ? 'profile' : 'campaigns'" in app_code

    # #/campaigns/:id/characters disambiguation from #/campaigns/:id
    assert "#/campaigns/:campaignId/characters" in app_code
    assert "pat.startsWith('#/campaigns/:campaignId')" in app_code

    # #/characters/:characterId disambiguation from #/characters
    assert "pat.startsWith('#/characters/') && pat !== '#/characters'" in app_code
    assert "pat === '#/characters'" in app_code


# ---------------------------------------------------------------------------
# 3. Route-Bound WebSocket Lifecycle & Teardown Architecture
# ---------------------------------------------------------------------------


def test_route_bound_websocket_lifecycle_and_teardown():
    """Verify WebSocket connects exclusively on session routes and tears down cleanly."""
    app_code = APP_TS.read_text(encoding="utf-8")

    assert "manageWebSocketLifecycle" in app_code
    assert "connectWebSocket" in app_code
    assert "disconnectWebSocket" in app_code
    assert "registerTeardown" in app_code

    # WebSocket connected only for session routes
    assert "route.pattern.includes('/sessions/') || route.pattern.includes('/lobby/')" in app_code
    assert "/ws/session/" in app_code


# ---------------------------------------------------------------------------
# 4. Dynamic Route Title & Breadcrumb Resolution Architecture
# ---------------------------------------------------------------------------


def test_dynamic_title_and_breadcrumb_resolver_api():
    """Verify router declares synchronous and asynchronous title resolvers with caching."""
    router_code = ROUTER_TS.read_text(encoding="utf-8")

    assert "setTitleResolver(" in router_code
    assert "setAsyncTitleResolver(" in router_code
    assert "setRouteTitle(" in router_code
    assert "resolveTitle(" in router_code
    assert "resolveTitleAsync(" in router_code
    assert "routeTitles: Map<string, string>" in router_code


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


def test_gateway_frontdoor_endpoints_for_audited_views():
    """Verify Gateway API provides public frontdoor endpoints required by all audited views."""
    headers = {"X-User-Id": "user-valeros"}

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
