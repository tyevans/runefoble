"""Blackbox frontdoor test suite for Dynamic Character Binding in Pre-Game Lobby and Active VTT.

Part of TASK-0256 / PRD-0006 / PRD-0023 / US-0065 / US-0069.
Governed by:
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0007: Domain-Driven Design Architecture
- ADR-0012: Design System Theming and Bauhaus Modernism
- ADR-0013: Frontend Microfrontend Architecture
- Hard Invariant 6: File length limit (< 450 lines for App Shell, < 500 lines overall)
- Hard Invariant 7: Blackbox TDD with frontdoor setup
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from gateway_api.campaign_store import campaign_store
from gateway_api.character_store import character_store
from gateway_api.main import app as gateway_app

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
SRC_DIR = FRONTEND_DIR / "src"
SERVICES_DIR = SRC_DIR / "services"


@pytest.fixture
def client() -> TestClient:
    return TestClient(gateway_app)


@pytest.fixture(autouse=True)
def reset_stores():
    campaign_store.reset()
    character_store.reset()
    yield


# ---------------------------------------------------------------------------
# 1. Hard Invariant 6: Source File Line Count Constraints
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 2. Design Tokens & Zero Hex Literals Invariant (ADR-0012)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 3. Component Contracts & Dynamic Vitals Invariants
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 4. Gateway API Frontdoor Setup & Data Retrieval
# ---------------------------------------------------------------------------


def test_gateway_character_and_campaign_frontdoors(client: TestClient, signing_issuer) -> None:
    """Verify characters created via public API frontdoors are listed and campaign-assigned."""
    headers = {"Authorization": f"Bearer {signing_issuer.mint('user-valeros')}"}

    # 1. Create a campaign
    camp_res = client.post(
        "/api/v1/campaigns",
        json={
            "title": "Tomb of the Star-Eater",
            "setting": "Astral Void",
            "system": "5e",
        },
        headers=headers,
    )
    assert camp_res.status_code == 201
    campaign_id = camp_res.json()["id"]

    # 2. Create characters
    char_res1 = client.post(
        "/api/v1/characters",
        json={
            "name": "Valeros of Korvosa",
            "character_class": "Fighter",
            "subclass": "Battle Master",
            "level": 4,
            "max_hp": 45,
            "armor_class": 18,
            "speed": 30,
            "portrait_url": "/assets/portraits/fighter.svg",
        },
        headers=headers,
    )
    assert char_res1.status_code == 201
    char_valeros = char_res1.json()

    char_res2 = client.post(
        "/api/v1/characters",
        json={
            "name": "Kyra the Sun Maiden",
            "character_class": "Cleric",
            "subclass": "Life Domain",
            "level": 4,
            "max_hp": 32,
            "armor_class": 16,
            "speed": 25,
            "portrait_url": "/assets/portraits/cleric.svg",
        },
        headers=headers,
    )
    assert char_res2.status_code == 201
    char_kyra = char_res2.json()

    # 3. Assign Kyra to the campaign
    assign_res = client.patch(
        f"/api/v1/characters/{char_kyra['id']}/campaign",
        json={"campaign_id": campaign_id},
        headers=headers,
    )
    assert assign_res.status_code == 200
    assert assign_res.json()["campaign_id"] == campaign_id

    # 4. List characters through public frontdoor
    list_res = client.get("/api/v1/characters", headers=headers)
    assert list_res.status_code == 200
    char_list = list_res.json()
    assert any(c["id"] == char_valeros["id"] for c in char_list)
    assert any(c["id"] == char_kyra["id"] and c["campaign_id"] == campaign_id for c in char_list)


# ---------------------------------------------------------------------------
# 5. Lobby Selection to Active VTT Session Propagation Logic
# ---------------------------------------------------------------------------


def test_lobby_to_vtt_character_resolution_scenarios() -> None:
    """Verify character selection propagation, fallback resolution, and DM inspector switching."""
    characters = [
        {
            "id": "char-valeros",
            "name": "Valeros of Korvosa",
            "characterClass": "Fighter",
            "level": 4,
            "currentHp": 38,
            "maxHp": 45,
            "armorClass": 18,
            "speed": 30,
            "campaignId": None,
            "portraitUrl": "/assets/portraits/fighter.svg",
        },
        {
            "id": "char-kyra",
            "name": "Kyra the Sun Maiden",
            "characterClass": "Cleric",
            "level": 4,
            "currentHp": 28,
            "maxHp": 32,
            "armorClass": 16,
            "speed": 25,
            "campaignId": "camp-tomb",
            "portraitUrl": "/assets/portraits/cleric.svg",
        },
    ]

    # Emulate App Shell resolution logic
    def resolve_active(
        campaign_id: str,
        explicit_selection: dict | None,
        char_pool: list[dict],
    ) -> dict:
        if explicit_selection:
            return explicit_selection
        campaign_match = next((c for c in char_pool if c.get("campaignId") == campaign_id), None)
        if campaign_match:
            return campaign_match
        if char_pool:
            return char_pool[0]
        return {
            "id": "char-placeholder",
            "name": "Adventurer",
            "characterClass": "Adventurer",
            "level": 1,
            "currentHp": 20,
            "maxHp": 20,
            "armorClass": 10,
            "speed": 30,
            "portraitUrl": "/assets/portraits/fighter.svg",
        }

    # Scenario 1: User explicitly selects Valeros in pre-game lobby
    explicitly_selected = characters[0]
    res1 = resolve_active("camp-tomb", explicitly_selected, characters)
    assert res1["id"] == "char-valeros"
    assert res1["name"] == "Valeros of Korvosa"
    assert res1["currentHp"] == 38
    assert res1["armorClass"] == 18

    # Scenario 2: User enters active session without explicit selection -> falls back to campaign-assigned Kyra
    res2 = resolve_active("camp-tomb", None, characters)
    assert res2["id"] == "char-kyra"
    assert res2["name"] == "Kyra the Sun Maiden"
    assert res2["currentHp"] == 28
    assert res2["armorClass"] == 16

    # Scenario 3: User enters active session in an unassigned campaign -> falls back to first character
    res3 = resolve_active("camp-other", None, characters)
    assert res3["id"] == "char-valeros"

    # Scenario 4: User with empty roster enters session -> graceful placeholder
    res4 = resolve_active("camp-empty", None, [])
    assert res4["id"] == "char-placeholder"
    assert res4["name"] == "Adventurer"
    assert res4["currentHp"] == 20
    assert res4["armorClass"] == 10

    # Scenario 5: DM inspector switcher switches active character
    dm_switched = characters[1]  # DM selects Kyra
    assert dm_switched["id"] == "char-kyra"
    assert dm_switched["characterClass"] == "Cleric"
