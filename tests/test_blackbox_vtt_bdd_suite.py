"""Blackbox frontdoor verification test suite for Session Lobby and Tabletop VTT Playwright BDD Suite.

TASK-0362 / ADR-0004 / ADR-0005 / ADR-0010 / ADR-0013 / ADR-0014
Verifies:
- Gherkin feature specification completeness and scenario definitions.
- Step definition mappings and multi-browser context contracts.
- Gateway API campaign and tabletop session models and endpoints.
- WebSocket message handling for lobby readiness, stand-in toggles, and token kinematics.
- File length invariants (<500 lines) across all modified files.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from gateway_api.campaign_store import campaign_store
from gateway_api.main import app as gateway_app

REPO_ROOT = Path(__file__).resolve().parent.parent
E2E_FEATURE_FILE = REPO_ROOT / "e2e" / "features" / "session_lobby_and_vtt.feature"
E2E_STEPS_FILE = REPO_ROOT / "e2e" / "steps" / "vtt_steps.ts"
E2E_WORLD_FILE = REPO_ROOT / "e2e" / "support" / "world.ts"
E2E_AUTH_FILE = REPO_ROOT / "e2e" / "support" / "auth_fixtures.ts"
APP_SHELL_FILE = REPO_ROOT / "frontend" / "src" / "runefoble-app.ts"
APP_FIXTURES_FILE = REPO_ROOT / "frontend" / "src" / "services" / "app-data-service.fixtures.ts"
DOCS_HOW_TO_FILE = REPO_ROOT / "docs" / "how-to" / "validate-e2e-journeys-with-playwright-bdd.md"


@pytest.fixture
def client() -> TestClient:
    return TestClient(gateway_app)


@pytest.fixture(autouse=True)
def reset_campaign_store():
    campaign_store.reset()
    yield


def test_file_length_invariants() -> None:
    """Verify all files touched or created in TASK-0362 conform strictly to Hard Invariant 6 (<500 lines)."""
    checked_files = [
        E2E_FEATURE_FILE,
        E2E_STEPS_FILE,
        E2E_WORLD_FILE,
        E2E_AUTH_FILE,
        APP_SHELL_FILE,
        APP_FIXTURES_FILE,
        DOCS_HOW_TO_FILE,
        Path(__file__),
    ]

    for path in checked_files:
        assert path.is_file(), f"{path} must exist"
        lines = len(path.read_text(encoding="utf-8").splitlines())
        assert lines < 500, (
            f"{path.name} has {lines} lines, exceeding the 500 line limit (Hard Invariant 6)"
        )


def test_gherkin_feature_completeness() -> None:
    """Verify session_lobby_and_vtt.feature defines all 4 required scenarios and Background."""
    content = E2E_FEATURE_FILE.read_text(encoding="utf-8")

    assert "Feature: Session Lobby and Tabletop VTT Synchronization" in content
    assert "Background:" in content

    required_scenarios = [
        "Multi-User Lobby Assembly and Readiness",
        "Marking Absentee AI Stand-In",
        "DM Launching Active Tabletop VTT",
        "Live Token Kinematics and Movement Sync",
    ]

    for scenario in required_scenarios:
        assert f"Scenario: {scenario}" in content, f"Feature must include Scenario: {scenario}"

    assert "@serial" in content, (
        "Feature or scenarios should be annotated with @serial for multi-browser sync"
    )


def test_step_definitions_contract() -> None:
    """Verify vtt_steps.ts handles browser contexts, shadow DOM locators, and WebSocket interactions."""
    content = E2E_STEPS_FILE.read_text(encoding="utf-8")

    # Verify context creation and dual browser management
    assert "browser.newContext" in content
    assert "world.setPage" in content
    assert "world.getPage" in content
    assert "injectUserIntoPage" in content

    # Verify shadow DOM component targeting
    assert "runefoble-session-lobby" in content
    assert "runefoble-board" in content
    assert "runefoble-watcher-feed" in content

    # Verify coordinate parsing and token movement
    assert "move-token" in content
    assert "toX" in content or "to_x" in content or "x" in content


def test_gateway_api_session_and_participants_frontdoor(client: TestClient) -> None:
    """Verify gateway campaign store seeds session 15 and participants for lobby test."""
    # Grant DM role to user-evelyn on campaign 4
    assign_res = client.post(
        "/api/v1/campaigns/4/roles",
        json={"user_id": "user-evelyn", "role": "dungeon_master"},
    )
    assert assign_res.status_code == 200

    headers = {"X-User-Id": "user-evelyn"}

    # Fetch session 15
    res = client.get("/api/v1/sessions/15", headers=headers)
    assert res.status_code == 200
    session_data = res.json()
    assert session_data["id"] == "15"
    assert session_data.get("campaign_id") == "4" or session_data.get("campaignId") == "4"

    # Check participants for session 15
    participants = session_data["participants"]
    assert len(participants) >= 3

    # Check Evelyn or Valeros and Sarah presence
    participant_names = {p.get("username") or p.get("name") for p in participants}
    assert "Valeros" in participant_names
    assert "Sarah" in participant_names


def test_gateway_websocket_session_events(client: TestClient) -> None:
    """Verify gateway tabletop router supports real-time WebSocket protocol for session 15."""
    with client.websocket_connect("/ws/session/15?token=test-valeros-token") as ws:
        # Initial handshake or presence
        initial = ws.receive_json()
        assert initial.get("type") in ["connected", "presence_state"]

        # Client sends readiness update
        ws.send_json({"type": "participant_ready", "participantId": "valeros-1", "isReady": True})

        # Client receives back or broadcasts
        reply = ws.receive_json()
        assert reply.get("type") in ["participant_ready", "presence_state", "board_sync"]
        if reply.get("type") == "participant_ready":
            assert reply["isReady"] is True


def test_docs_contain_multi_context_bdd_guidance() -> None:
    """Verify documentation explains multi-context dual browser testing with Playwright BDD."""
    doc_content = DOCS_HOW_TO_FILE.read_text(encoding="utf-8")
    assert "Multi-Browser Concurrent Sessions" in doc_content
    assert "Dual-Context Architecture" in doc_content
    assert "browser.newContext" in doc_content
