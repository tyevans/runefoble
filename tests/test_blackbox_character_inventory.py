"""Blackbox tests verifying character inventory, equipment, and condition management via public frontdoors.

Complies strictly with Hard Invariant 7 (Blackbox TDD with Frontdoor Setup):
All assertions and state mutations flow through public HTTP routes and OpenAPI contracts.
"""

import pytest
from character_sheet.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    return TestClient(app)


def test_blackbox_inventory_stacking_and_partial_removal(client):
    """Verify adding stackable items and partial vs complete consumption via public HTTP endpoints."""
    # 1. Frontdoor create character
    create_resp = client.post(
        "/api/v1/characters/create",
        json={"name": "Krag", "character_class": "Barbarian", "max_hp": 55},
    )
    assert create_resp.status_code == 200
    char_id = create_resp.json()["character_id"]

    # 2. Add rations (stack of 10)
    add_rations = client.post(
        f"/api/v1/characters/{char_id}/inventory/add",
        json={"item_id": "ration-001", "name": "Trail Rations", "quantity": 10, "weight_lbs": 10.0},
    )
    assert add_rations.status_code == 200
    inv = add_rations.json()["inventory"]
    assert inv["ration-001"]["quantity"] == 10
    assert inv["ration-001"]["weight_lbs"] == 10.0

    # 3. Add second item: Greatsword
    add_sword = client.post(
        f"/api/v1/characters/{char_id}/inventory/add",
        json={"item_id": "sword-001", "name": "Iron Greatsword", "quantity": 1, "weight_lbs": 6.0},
    )
    assert add_sword.status_code == 200
    assert "sword-001" in add_sword.json()["inventory"]
    assert len(add_sword.json()["inventory"]) == 2

    # 4. Consume partial rations (consume 4)
    consume_resp = client.post(
        f"/api/v1/characters/{char_id}/inventory/ration-001/remove",
        json={"quantity": 4},
    )
    assert consume_resp.status_code == 200
    assert consume_resp.json()["inventory"]["ration-001"]["quantity"] == 6

    # 5. Consume remaining rations (consume 6) -> removes entry completely
    consume_all = client.post(
        f"/api/v1/characters/{char_id}/inventory/ration-001/remove",
        json={"quantity": 6},
    )
    assert consume_all.status_code == 200
    assert "ration-001" not in consume_all.json()["inventory"]

    # 6. Removing non-existent item returns 404 or 400
    err_resp = client.post(
        f"/api/v1/characters/{char_id}/inventory/nonexistent/remove",
        json={"quantity": 1},
    )
    assert err_resp.status_code in (400, 404)


def test_blackbox_equipment_slots_workflow(client):
    """Verify equipping across main_hand, off_hand, and armor slots, plus un-equipping."""
    create_resp = client.post(
        "/api/v1/characters/create",
        json={"name": "Alanna", "character_class": "Paladin", "max_hp": 48},
    )
    assert create_resp.status_code == 200
    char_id = create_resp.json()["character_id"]

    # Add items to inventory first
    client.post(
        f"/api/v1/characters/{char_id}/inventory/add",
        json={"item_id": "sword-paladin", "name": "Sun Blade", "quantity": 1, "weight_lbs": 3.0},
    )
    client.post(
        f"/api/v1/characters/{char_id}/inventory/add",
        json={"item_id": "shield-paladin", "name": "Kite Shield", "quantity": 1, "weight_lbs": 6.0},
    )

    # Equip main hand
    eq_main = client.post(
        f"/api/v1/characters/{char_id}/equipment",
        json={"slot": "main_hand", "item_name": "Sun Blade"},
    )
    assert eq_main.status_code == 200
    assert eq_main.json()["equipment"]["main_hand"] == "Sun Blade"

    # Equip off hand
    eq_off = client.post(
        f"/api/v1/characters/{char_id}/equipment",
        json={"slot": "off_hand", "item_name": "Kite Shield"},
    )
    assert eq_off.status_code == 200
    assert eq_off.json()["equipment"]["off_hand"] == "Kite Shield"

    # Unequip off hand (setting item_name to None)
    uneq_off = client.post(
        f"/api/v1/characters/{char_id}/equipment",
        json={"slot": "off_hand", "item_name": None},
    )
    assert uneq_off.status_code == 200
    assert "off_hand" not in uneq_off.json()["equipment"]


def test_blackbox_conditions_lifecycle(client):
    """Verify applying, querying, and removing conditions via frontdoor HTTP endpoints."""
    create_resp = client.post(
        "/api/v1/characters/create",
        json={"name": "Merisiel", "character_class": "Rogue", "max_hp": 30},
    )
    assert create_resp.status_code == 200
    char_id = create_resp.json()["character_id"]

    # Apply conditions: poisoned and stunned
    cond1 = client.post(
        f"/api/v1/characters/{char_id}/conditions",
        json={"condition": "poisoned", "duration_rounds": 5, "source": "Dart Trap"},
    )
    assert cond1.status_code == 200
    assert "poisoned" in cond1.json()["conditions"]
    assert cond1.json()["conditions"]["poisoned"]["duration_rounds"] == 5

    cond2 = client.post(
        f"/api/v1/characters/{char_id}/conditions",
        json={"condition": "stunned", "duration_rounds": 1, "source": "Mind Flayer Blast"},
    )
    assert cond2.status_code == 200
    assert "stunned" in cond2.json()["conditions"]
    assert len(cond2.json()["conditions"]) == 2

    # Query character state
    char_state = client.get(f"/api/v1/characters/{char_id}")
    assert char_state.status_code == 200
    assert "poisoned" in char_state.json()["conditions"]
    assert "stunned" in char_state.json()["conditions"]

    # Remove poisoned condition
    rem_resp = client.delete(f"/api/v1/characters/{char_id}/conditions/poisoned")
    assert rem_resp.status_code == 200
    assert "poisoned" not in rem_resp.json()["conditions"]
    assert "stunned" in rem_resp.json()["conditions"]

    # Removing non-active condition returns 400 or 404
    rem_err = client.delete(f"/api/v1/characters/{char_id}/conditions/blinded")
    assert rem_err.status_code in (400, 404)
