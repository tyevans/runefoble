"""Shared fixtures and test client setup for character sheet models tests."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from character_sheet.main import app
from character_sheet.models import CharacterState
from fastapi.testclient import TestClient


@pytest.fixture
def test_client() -> TestClient:
    """Provide FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def sample_character_payload() -> dict[str, Any]:
    """Sample payload for character creation via HTTP frontdoor."""
    return {
        "name": "Eldrin Swift",
        "character_class": "Wizard",
        "max_hp": 22,
        "personality_traits": ["studious", "curious"],
        "armor_class": 12,
        "speed_ft": 30,
        "ability_scores": {"str": 8, "dex": 14, "con": 12, "int": 17, "wis": 13, "cha": 10},
    }


@pytest.fixture
def sample_character_state() -> CharacterState:
    """Sample initialized CharacterState domain model."""
    return CharacterState.initial(
        character_id=uuid4(),
        name="Thorne Ironfoot",
        character_class="Paladin",
        max_hp=40,
        current_hp=40,
        player_id="player-thorn",
        personality_traits=["resolute", "just"],
        campaign_id="camp-101",
        subclass="Oath of the Ancients",
        armor_class=18,
        speed_ft=30,
        ability_scores={"str": 16, "dex": 10, "con": 14, "int": 10, "wis": 12, "cha": 14},
    )
