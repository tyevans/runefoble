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

import pytest
from fastapi.testclient import TestClient

from tests.helpers.game_session_app import session_app
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.fixture
def client() -> TestClient:
    return TestClient(
        session_app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"}
    )


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


# ---------------------------------------------------------------------------
# 2. Campaign Dashboard Component Contracts & UI Invariants
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 3. Campaign Creator Component Contracts & UI Invariants
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 4. Design Tokens & Zero Hex Literals Invariant (ADR-0012)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 6. Storybook Stories
# ---------------------------------------------------------------------------
