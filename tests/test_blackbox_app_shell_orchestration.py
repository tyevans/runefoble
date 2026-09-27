"""Blackbox TDD frontdoor test suite for App Shell View Orchestration & Session Transition.

Part of TASK-0213 / PRD-0023 / US-0065 / US-0066.
Governing ADRs:
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0012: Design System Theming and Bauhaus Modernism
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 6: File length limit (< 450 lines for App Shell, < 500 lines overall)
- Hard Invariant 7: Blackbox TDD with frontdoor setup
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from gateway_api.campaign_store import campaign_store
from gateway_api.main import app as gateway_app

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
SRC_DIR = FRONTEND_DIR / "src"
COMPONENTS_DIR = SRC_DIR / "components"
SERVICES_DIR = SRC_DIR / "services"


@pytest.fixture
def client() -> TestClient:
    return TestClient(gateway_app)


@pytest.fixture(autouse=True)
def reset_store():
    campaign_store.reset()
    yield


# ---------------------------------------------------------------------------
# 1. Hard Invariant 6: Source File Line Count Constraints
# ---------------------------------------------------------------------------


def test_app_shell_file_length_invariants() -> None:
    """Verify runefoble-app.ts is strictly kept under 450 lines (Hard Invariant 6)."""
    app_ts = SRC_DIR / "runefoble-app.ts"
    assert app_ts.is_file(), f"{app_ts} must exist"

    lines = app_ts.read_text(encoding="utf-8").splitlines()
    assert len(lines) <= 450, f"runefoble-app.ts has {len(lines)} lines; must be <= 450 lines"

    # Also verify associated decomposed components are well under 500 lines
    session_list_ts = COMPONENTS_DIR / "runefoble-session-list.ts"
    assert session_list_ts.is_file(), f"{session_list_ts} must exist"
    assert len(session_list_ts.read_text(encoding="utf-8").splitlines()) < 500

    app_data_service_ts = SERVICES_DIR / "app-data-service.ts"
    assert app_data_service_ts.is_file(), f"{app_data_service_ts} must exist"
    assert len(app_data_service_ts.read_text(encoding="utf-8").splitlines()) < 500


# ---------------------------------------------------------------------------
# 2. Dynamic View Rendering & Microfrontend Orchestration
# ---------------------------------------------------------------------------


def test_app_shell_orchestrates_required_views() -> None:
    """Verify runefoble-app.ts imports and mounts all required subviews by route."""
    app_code = (SRC_DIR / "runefoble-app.ts").read_text(encoding="utf-8")

    # Verify custom element registration
    assert "@customElement('runefoble-app')" in app_code
    assert "class RunefobleApp extends LitElement" in app_code

    # Verify routed microfrontends and views are mounted
    assert "runefoble-auth-modal" in app_code
    assert "runefoble-campaign-dashboard" in app_code
    assert "runefoble-campaign-members" in app_code
    assert "runefoble-session-list" in app_code
    assert "runefoble-character-roster" in app_code
    assert "runefoble-session-lobby" in app_code
    assert "runefoble-board" in app_code
    assert "runefoble-character-card" in app_code
    assert "runefoble-watcher-feed" in app_code
    assert "runefoble-voice-controls" in app_code


def test_app_shell_route_bound_websocket_lifecycle() -> None:
    """Verify runefoble-app.ts binds WebSocket connections to session routes only."""
    app_code = (SRC_DIR / "runefoble-app.ts").read_text(encoding="utf-8")

    # Verify WebSocket connection is managed on route change
    assert "manageWebSocketLifecycle" in app_code
    assert "connectWebSocket" in app_code
    assert "disconnectWebSocket" in app_code

    # Verify teardown registration on router
    assert "registerTeardown" in app_code

    # Verify WebSocket connects to session routes
    assert "/ws/session/" in app_code
    assert "lobby" in app_code
    assert "sessions" in app_code


def test_app_shell_session_start_transition() -> None:
    """Verify runefoble-app.ts implements transition from lobby to active VTT session."""
    app_code = (SRC_DIR / "runefoble-app.ts").read_text(encoding="utf-8")

    # Handles launch-session event
    assert "handleLaunchSession" in app_code
    assert "@launch-session" in app_code

    # Handles session_started WS message
    assert "session_started" in app_code


# ---------------------------------------------------------------------------
# 3. Gateway Frontdoor API Endpoints Parameterized by Route
# ---------------------------------------------------------------------------


def test_gateway_campaign_and_session_routes(client: TestClient) -> None:
    """Verify Gateway API provides required frontdoor endpoints for route data fetching."""
    headers = {"X-User-Id": "user-valeros"}

    # 1. Create a campaign
    camp_res = client.post(
        "/api/v1/campaigns",
        json={"title": "Tomb of the Star-Eater", "setting": "Spelljammer", "system": "5e"},
        headers=headers,
    )
    assert camp_res.status_code == 201
    campaign_id = camp_res.json()["id"]

    # 2. Fetch campaign list (for #/campaigns)
    list_res = client.get("/api/v1/campaigns", headers=headers)
    assert list_res.status_code == 200
    assert any(c["id"] == campaign_id for c in list_res.json())

    # 3. Fetch campaign detail (for #/campaigns/:campaignId)
    detail_res = client.get(f"/api/v1/campaigns/{campaign_id}", headers=headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["title"] == "Tomb of the Star-Eater"

    # 4. Fetch campaign members (for #/campaigns/:campaignId)
    members_res = client.get(f"/api/v1/campaigns/{campaign_id}/members", headers=headers)
    assert members_res.status_code == 200
    assert len(members_res.json()) >= 1

    # 5. Fetch session details (for #/campaigns/:campaignId/lobby/:sessionId)
    session_res = client.get(f"/api/v1/sessions/{campaign_id}", headers=headers)
    assert session_res.status_code == 200
    assert session_res.json()["id"] == campaign_id

    # 6. Fetch board tokens (for #/campaigns/:campaignId/sessions/:sessionId)
    board_res = client.get(f"/api/v1/boards/{campaign_id}", headers=headers)
    assert board_res.status_code == 200
    assert "tokens" in board_res.json()
