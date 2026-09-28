"""FastAPI route integration tests verifying public HTTP frontdoors."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient


def test_character_creation_and_query_frontdoor(
    test_client: TestClient, sample_character_payload: dict[str, Any]
) -> None:
    """Verify character creation and fetching via HTTP endpoints."""
    create_res = test_client.post("/api/v1/characters", json=sample_character_payload)
    assert create_res.status_code == 200, create_res.text
    char_data = create_res.json()
    char_id = char_data["character_id"]
    assert char_data["name"] == "Eldrin Swift"
    assert char_data["level"] == 1
    assert char_data["ability_scores"]["int"] == 17

    get_res = test_client.get(f"/api/v1/characters/{char_id}")
    assert get_res.status_code == 200
    assert get_res.json()["character_id"] == char_id


def test_character_inventory_and_equipment_routes(
    test_client: TestClient, sample_character_payload: dict[str, Any]
) -> None:
    """Verify item addition and equipment slot assignment endpoints."""
    create_res = test_client.post("/api/v1/characters", json=sample_character_payload)
    char_id = create_res.json()["character_id"]

    add_item_res = test_client.post(
        f"/api/v1/characters/{char_id}/inventory/add",
        json={"item_id": "it-wand-1", "name": "Wand of Sparks", "quantity": 1, "weight_lbs": 1.0},
    )
    assert add_item_res.status_code == 200
    assert "it-wand-1" in add_item_res.json()["inventory"]

    equip_res = test_client.post(
        f"/api/v1/characters/{char_id}/equipment",
        json={"slot": "main_hand", "item_name": "Wand of Sparks"},
    )
    assert equip_res.status_code == 200
    assert equip_res.json()["equipment"]["main_hand"] == "Wand of Sparks"


def test_character_conditions_and_progression_routes(
    test_client: TestClient, sample_character_payload: dict[str, Any]
) -> None:
    """Verify condition application, level up, and spell preparation endpoints."""
    create_res = test_client.post("/api/v1/characters", json=sample_character_payload)
    char_id = create_res.json()["character_id"]

    cond_res = test_client.post(
        f"/api/v1/characters/{char_id}/conditions",
        json={"condition": "poisoned", "duration_rounds": 2, "source": "viper"},
    )
    assert cond_res.status_code == 200
    assert "poisoned" in cond_res.json()["conditions"]

    lvl_res = test_client.post(
        f"/api/v1/characters/{char_id}/level-up",
        json={"target_level": 2, "hp_increase": 6},
    )
    assert lvl_res.status_code == 200
    assert lvl_res.json()["level"] == 2
    assert lvl_res.json()["max_hp"] == 28

    prep_res = test_client.post(
        f"/api/v1/characters/{char_id}/spells/prepare",
        json={"spell_name": "Magic Missile", "spell_level": 1},
    )
    assert prep_res.status_code == 200
    assert "Magic Missile" in prep_res.json()["prepared_spells"]
