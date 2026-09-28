"""Blackbox frontdoor tests for Session Scheduling and Staging Lobby Creation Modal.

TASK-0249: Session Scheduling and Staging Lobby Creation Modal.
Governing ADRs: ADR-0001 (SpiceDB Zanzibar), ADR-0004 (Lit Web Components),
ADR-0007 (Gateway API), ADR-0012 (Design System Theming and Bauhaus Modernism).
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
STORIES_DIR = SRC_DIR / "stories"

MODAL_TS = COMPONENTS_DIR / "runefoble-session-modal.ts"
LIST_TS = COMPONENTS_DIR / "runefoble-session-list.ts"
STORIES_TS = STORIES_DIR / "runefoble-session-modal.stories.ts"
APP_TS = SRC_DIR / "runefoble-app.ts"
INDEX_TS = SRC_DIR / "index.ts"


@pytest.fixture
def client() -> TestClient:
    return TestClient(gateway_app)


@pytest.fixture(autouse=True)
def reset_store():
    campaign_store.reset()
    yield


# ---------------------------------------------------------------------------
# 1. Hard Invariant 6: Source File Line Count Constraints (< 500 lines)
# ---------------------------------------------------------------------------


def test_file_length_invariants():
    """Verify all related source files strictly adhere to the <500 lines limit."""
    files_to_check = [MODAL_TS, LIST_TS, STORIES_TS, APP_TS, INDEX_TS]
    for file_path in files_to_check:
        assert file_path.is_file(), f"{file_path} must exist"
        lines = file_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) < 500, f"{file_path.name} has {len(lines)} lines; must be < 500"


# ---------------------------------------------------------------------------
# 2. Lit Component Registration, Properties, and Shadow DOM Contract
# ---------------------------------------------------------------------------


def test_session_modal_component_registration_and_properties():
    """Verify runefoble-session-modal custom element registration and properties."""
    content = MODAL_TS.read_text(encoding="utf-8")
    assert "@customElement('runefoble-session-modal')" in content
    assert "class RunefobleSessionModal extends LitElement" in content
    assert "@property({ type: Boolean, reflect: true }) open = false;" in content
    assert "@property({ type: String, attribute: 'campaign-id' }) campaignId = '';" in content
    assert "@property({ type: String }) errorMessage = '';" in content
    assert "'runefoble-session-modal': RunefobleSessionModal;" in content


def test_session_modal_form_fields_and_accessibility():
    """Verify required form fields, accessibility ARIA attributes, and dialog shell."""
    content = MODAL_TS.read_text(encoding="utf-8")

    # Dialog accessibility
    assert 'role="dialog"' in content
    assert 'aria-modal="true"' in content
    assert 'aria-labelledby="session-modal-title"' in content
    assert 'aria-label="Close modal"' in content

    # Form fields
    assert 'id="session-title"' in content
    assert 'id="session-status"' in content
    assert 'id="scheduled-at"' in content
    assert 'id="session-description"' in content

    # Status options
    assert 'value="lobby"' in content
    assert 'value="upcoming"' in content

    # Action buttons
    assert 'class="btn-cancel"' in content
    assert 'class="btn-submit"' in content
    assert "Create Session" in content

    # Keyboard / backdrop handling
    assert "Escape" in content
    assert "handleKeyDown" in content
    assert "handleBackdropClick" in content


def test_session_modal_bauhaus_tokens_and_theming():
    """Verify Bauhaus modernism design tokens and high-contrast styles."""
    content = MODAL_TS.read_text(encoding="utf-8")
    assert "var(--rf-bg-surface" in content
    assert "var(--rf-text-primary" in content
    assert "var(--rf-border-width" in content
    assert "var(--rf-border-color" in content
    assert "var(--rf-shadow" in content
    assert "var(--rf-accent-primary" in content
    assert "var(--rf-accent-secondary" in content


# ---------------------------------------------------------------------------
# 3. Component Interaction & Event Dispatch Contract
# ---------------------------------------------------------------------------


def test_session_modal_event_emission_and_validation():
    """Verify validation and @create-session event payload contract."""
    content = MODAL_TS.read_text(encoding="utf-8")

    # Validation
    assert "Session title is required" in content
    assert "error-banner" in content
    assert 'role="alert"' in content

    # CustomEvent dispatch
    assert "new CustomEvent('create-session'" in content
    assert "bubbles: true" in content
    assert "composed: true" in content
    assert "title: this.sessionTitle.trim()" in content
    assert "scheduledAt:" in content
    assert "description:" in content
    assert "status: this.status" in content

    # Modal closed event
    assert "new CustomEvent('modal-closed'" in content


def test_session_list_integration_with_modal():
    """Verify runefoble-session-list hosts runefoble-session-modal and triggers it."""
    list_content = LIST_TS.read_text(encoding="utf-8")

    # Imports and hosts modal
    assert "import './runefoble-session-modal.ts'" in list_content
    assert "<runefoble-session-modal" in list_content
    assert "isCreateModalOpen" in list_content
    assert "openCreateModal" in list_content
    assert "closeCreateModal" in list_content

    # Button triggers modal opening
    assert "+ New Session" in list_content
    assert "handleCreateSession" in list_content
    assert "this.isCreateModalOpen = true" in list_content


def test_app_shell_create_session_event_handling():
    """Verify runefoble-app handles @create-session and navigates conditionally."""
    app_content = APP_TS.read_text(encoding="utf-8")
    assert "@create-session=" in app_content
    assert "createCampaignSession" in app_content
    assert "fetchCampaignSessions" in app_content
    assert "lobby" in app_content


def test_index_exports_session_modal_and_list():
    """Verify runefoble-session-modal and runefoble-session-list are exported."""
    index_content = INDEX_TS.read_text(encoding="utf-8")
    assert "export * from './components/runefoble-session-list.ts';" in index_content
    assert "export * from './components/runefoble-session-modal.ts';" in index_content


# ---------------------------------------------------------------------------
# 4. Storybook Stories Completeness
# ---------------------------------------------------------------------------


def test_storybook_stories_completeness():
    """Verify Storybook stories exist for lobby, upcoming, validation errors, and themes."""
    assert STORIES_TS.is_file(), "runefoble-session-modal.stories.ts must exist"
    stories_content = STORIES_TS.read_text(encoding="utf-8")
    assert "Campaign/RunefobleSessionModal" in stories_content
    assert "DefaultOpenLobby" in stories_content
    assert "OpenUpcomingSession" in stories_content
    assert "ModalWithValidationError" in stories_content
    assert "DarkMode" in stories_content
    assert "LightMode" in stories_content
    assert "CyberRuneTheme" in stories_content
    assert "ParchmentTheme" in stories_content


# ---------------------------------------------------------------------------
# 5. Gateway API Frontdoor Contract Integration (ADR-0001, ADR-0007)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gateway_session_creation_and_listing_contract(client: TestClient):
    """Verify full frontdoor lifecycle for creating sessions (lobby and upcoming)."""
    headers_dm = {"X-User-Id": "dm_evelyn"}

    # 1. DM creates campaign
    res_camp = client.post(
        "/api/v1/campaigns",
        json={"title": "Curse of Strahd", "setting": "Barovia"},
        headers=headers_dm,
    )
    assert res_camp.status_code == 201
    campaign_id = res_camp.json()["id"]

    # 2. DM creates a staging lobby session via POST /api/v1/campaigns/{id}/sessions
    res_lobby = client.post(
        f"/api/v1/campaigns/{campaign_id}/sessions",
        json={
            "title": "Chapter 1: The Mists of Barovia",
            "status": "lobby",
            "description": "Party assembles at the tavern outskirts.",
        },
        headers=headers_dm,
    )
    assert res_lobby.status_code == 201
    lobby_data = res_lobby.json()
    assert lobby_data["title"] == "Chapter 1: The Mists of Barovia"
    assert lobby_data["status"] == "lobby"
    assert lobby_data["campaign_id"] == campaign_id
    lobby_session_id = lobby_data["id"]

    # 3. DM creates an upcoming scheduled session with scheduled_at
    res_upcoming = client.post(
        f"/api/v1/campaigns/{campaign_id}/sessions",
        json={
            "title": "Chapter 2: Castle Ravenloft",
            "status": "upcoming",
            "scheduled_at": "2026-10-31T20:00:00Z",
            "description": "Assault on the spire.",
        },
        headers=headers_dm,
    )
    assert res_upcoming.status_code == 201
    upcoming_data = res_upcoming.json()
    assert upcoming_data["title"] == "Chapter 2: Castle Ravenloft"
    assert upcoming_data["status"] == "upcoming"
    assert upcoming_data["scheduled_at"] == "2026-10-31T20:00:00Z"

    # 4. List campaign sessions via GET /api/v1/campaigns/{id}/sessions
    res_list = client.get(
        f"/api/v1/campaigns/{campaign_id}/sessions",
        headers=headers_dm,
    )
    assert res_list.status_code == 200
    sessions = res_list.json()
    assert len(sessions) == 2
    session_ids = [s["id"] for s in sessions]
    assert lobby_session_id in session_ids
    assert upcoming_data["id"] in session_ids


@pytest.mark.asyncio
async def test_unauthorized_user_cannot_create_session(client: TestClient):
    """Verify unauthorized users without run_session permission cannot create sessions."""
    headers_owner = {"X-User-Id": "dm_evelyn"}
    headers_stranger = {"X-User-Id": "stranger_bob"}

    res_camp = client.post(
        "/api/v1/campaigns",
        json={"title": "Lost Mine of Phandelver"},
        headers=headers_owner,
    )
    campaign_id = res_camp.json()["id"]

    # Stranger attempts to create session -> 403 Forbidden
    res_forbidden = client.post(
        f"/api/v1/campaigns/{campaign_id}/sessions",
        json={"title": "Unauthorized Session", "status": "lobby"},
        headers=headers_stranger,
    )
    assert res_forbidden.status_code == 403
    assert res_forbidden.json()["detail"]["error"] == "permission_denied"
