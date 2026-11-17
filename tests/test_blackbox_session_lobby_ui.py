"""Blackbox TDD frontdoor test suite for Session Lobby & Readiness UI.

Part of TASK-0212 / PRD-0023 / US-0065.
Governed by:
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0012: Design System Theming and Bauhaus Modernism
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 6: File length limit (< 260 lines for component, < 500 lines overall)
- Hard Invariant 7: Blackbox TDD with frontdoor setup
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from game_session.main import app as session_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(session_app)


# ---------------------------------------------------------------------------
# 1. Microfrontend Manifest & Package Structure Integrity
# ---------------------------------------------------------------------------


def test_session_lobby_manifest_frontdoor(client: TestClient) -> None:
    """Verify game_session service advertises runefoble-session-lobby via GET /ui/manifest."""
    response = client.get("/ui/manifest")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "game_session"
    assert data["package"] == "@runefoble/game-session-ui"
    assert data["version"] == "0.1.0"
    assert "runefoble-session-lobby" in data["components"]

    # Also test routed alias
    alias_res = client.get("/game_session/ui/manifest")
    assert alias_res.status_code == 200
    alias_data = alias_res.json()
    assert "runefoble-session-lobby" in alias_data["components"]


# ---------------------------------------------------------------------------
# 2. Session Lobby Component Contracts & UI Invariants
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 3. Design Tokens & Zero Hex Literals Invariant (ADR-0012)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 4. File Length Limits (< 260 lines DoD, < 500 lines Hard Invariant 6)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 5. Storybook Stories
# ---------------------------------------------------------------------------
