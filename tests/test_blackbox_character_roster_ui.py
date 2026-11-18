"""Blackbox TDD frontdoor test suite for Character Roster and Party Assignment UI.

Part of TASK-0211 / PRD-0023 / US-0064.
Governed by:
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0012: Design System Theming and Bauhaus Modernism
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 6: File length limit (< 500 lines, component < 260 lines)
- Hard Invariant 7: Blackbox TDD with frontdoor setup
"""

from __future__ import annotations

import pytest
from character_sheet.main import app as character_app
from fastapi.testclient import TestClient

from tests.helpers.ws_identity import SIGNING_ISSUER


def auth_headers(sub: str) -> dict[str, str]:
    """Return Bearer headers for a token that the service verifier accepts."""
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


@pytest.fixture
def client() -> TestClient:
    return TestClient(character_app, headers=auth_headers("character-owner"))


# ---------------------------------------------------------------------------
# 1. Microfrontend Manifest & Package Structure Integrity
# ---------------------------------------------------------------------------


def test_character_roster_manifest_frontdoor(client: TestClient) -> None:
    """Verify character_sheet service advertises roster components via GET /ui/manifest."""
    response = client.get("/ui/manifest")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "character_sheet"
    assert data["package"] == "@runefoble/character-sheet-ui"
    assert "runefoble-character-roster" in data["components"]
    assert "runefoble-character-builder-modal" in data["components"]


# ---------------------------------------------------------------------------
# 2. Component Contracts & UI Invariants
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


# ---------------------------------------------------------------------------
# 6. Public Frontdoor Character Creation API
# ---------------------------------------------------------------------------


def test_create_character_public_api_frontdoor(client: TestClient) -> None:
    """Verify public POST /api/v1/characters endpoint handles character creation."""
    payload = {
        "name": "Valeros",
        "character_class": "Fighter",
        "max_hp": 45,
        "player_id": "usr-marcus",
        "personality_traits": ["brave", "protective"],
    }
    response = client.post("/api/v1/characters", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Valeros"
    assert data["character_class"] == "Fighter"
    assert data["max_hp"] == 45
    assert data["current_hp"] == 45
    assert data["player_id"] == "usr-marcus"
    assert "character_id" in data
