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

import os
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
SRC_DIR = FRONTEND_DIR / "src"


@pytest.fixture
def client(game_session_upstream) -> Iterator[TestClient]:
    with TestClient(gateway_app) as gateway_client:
        yield gateway_client


def _auth(issuer, sub: str) -> dict[str, str]:
    """Return Bearer headers carrying a token that the gateway verifies for `sub`."""
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


# ---------------------------------------------------------------------------
# 1. Hard Invariant 6: Source File Line Count Constraints
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 2. Dynamic View Rendering & Microfrontend Orchestration
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 3. Gateway Frontdoor API Endpoints Parameterized by Route
# ---------------------------------------------------------------------------


def test_gateway_campaign_and_session_routes(client: TestClient, trusted_ws_issuer) -> None:
    """Verify Gateway API provides required frontdoor endpoints for route data fetching."""
    headers = _auth(trusted_ws_issuer, "user-valeros")

    # 1. Create a campaign
    camp_res = client.post(
        "/api/v1/campaigns",
        json={"title": "Tomb of the Star-Eater", "setting": "Spelljammer", "system": "5e"},
        headers=headers,
    )
    assert camp_res.status_code == 201
    campaign_id = camp_res.json()["id"]
    session_id = _owner_session(campaign_id, headers)

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
    session_res = client.get(f"/api/v1/sessions/{session_id}", headers=headers)
    assert session_res.status_code == 200
    assert session_res.json()["session_id"] == session_id

    # 6. Fetch board tokens (for #/campaigns/:campaignId/sessions/:sessionId)
    board_res = client.get(f"/api/v1/boards/{campaign_id}", headers=headers)
    assert board_res.status_code == 200
    assert "tokens" in board_res.json()


def _owner_session(campaign_id: str, headers: dict[str, str]) -> str:
    """Create a game session in a campaign through the owner's public game_session route."""
    url = os.environ["RUNEFOBLE_GAME_SESSION_URL"]
    res = httpx.post(
        f"{url}/api/v1/sessions/create",
        json={"campaign_id": campaign_id, "title": "Crypt"},
        headers=headers,
        timeout=5.0,
    )
    assert res.status_code == 200, res.text
    return res.json()["session_id"]
