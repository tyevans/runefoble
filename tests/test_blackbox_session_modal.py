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


def _auth(issuer, sub: str) -> dict[str, str]:
    """Return Bearer headers carrying a token that the gateway verifies for `sub`."""
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


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


# ---------------------------------------------------------------------------
# 2. Lit Component Registration, Properties, and Shadow DOM Contract
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 3. Component Interaction & Event Dispatch Contract
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 4. Storybook Stories Completeness
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 5. Gateway API Frontdoor Contract Integration (ADR-0001, ADR-0007)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gateway_session_creation_and_listing_contract(client: TestClient, signing_issuer):
    """Verify full frontdoor lifecycle for creating sessions (lobby and upcoming)."""
    headers_dm = _auth(signing_issuer, "dm_evelyn")

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
    assert len(sessions) == 3
    session_ids = [s["id"] for s in sessions]
    assert lobby_session_id in session_ids
    assert upcoming_data["id"] in session_ids
    assert any(s["title"] == "Session #1: Staging Lobby" for s in sessions)


@pytest.mark.asyncio
async def test_unauthorized_user_cannot_create_session(client: TestClient, signing_issuer):
    """Verify unauthorized users without run_session permission cannot create sessions."""
    headers_owner = _auth(signing_issuer, "dm_evelyn")
    headers_stranger = _auth(signing_issuer, "stranger_bob")

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
