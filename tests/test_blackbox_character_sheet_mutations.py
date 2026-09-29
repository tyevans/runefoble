"""Blackbox frontdoor tests for Character Sheet Sub-Resource Mutations & Event-Sourced Persistence (TASK-0356).

Governing ADRs: ADR-0001, ADR-0002, ADR-0004, ADR-0007, ADR-0013.
Verifies:
1. POST /api/v1/characters/{id}/health modifies HP, clamps to [0, maxHp], and triggers stand-in stabilization when <= 0.
2. POST /api/v1/characters/{id}/equipment and DELETE /api/v1/characters/{id}/equipment/{slot} updates equipped gear.
3. POST /api/v1/characters/{id}/inventory and DELETE /api/v1/characters/{id}/inventory/{item_id} adds/removes items.
4. POST /api/v1/characters/{id}/conditions and DELETE /api/v1/characters/{id}/conditions/{condition} manages conditions.
5. POST /api/v1/characters/{id}/spells/cast expends spell slots (and rejects if insufficient).
6. POST /api/v1/characters/{id}/spells/prepare toggles prepared spells.
7. Zanzibar authorization rejects non-permitted users with 403 Forbidden across all mutation endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from gateway_api.campaign_store import campaign_store
from gateway_api.character_store import character_store
from gateway_api.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_stores():
    """Reset character and campaign memory stores before each test."""
    character_store.reset(load_defaults=False)
    campaign_store.reset()
    yield


def create_test_character(owner_id: str = "user_valeros", is_stand_in: bool = False) -> str:
    """Helper to create a test character via frontdoor POST /api/v1/characters."""
    headers = {"X-User-Id": owner_id}
    res = client.post(
        "/api/v1/characters",
        json={
            "name": "Valeros of Korvosa",
            "characterClass": "Fighter 4 / Wizard 1",
            "level": 5,
            "currentHp": 38,
            "maxHp": 44,
            "armorClass": 18,
            "speed": 30,
            "isAiStandIn": is_stand_in,
        },
        headers=headers,
    )
    assert res.status_code == 201
    return res.json()["id"]


@pytest.mark.asyncio
async def test_health_modification_and_clamping():
    """Verify modifying HP with positive and negative deltas clamps within [0, maxHp]."""
    char_id = create_test_character()
    headers = {"X-User-Id": "user_valeros"}

    # Take 10 damage: 38 - 10 = 28
    res = client.post(
        f"/api/v1/characters/{char_id}/health",
        json={"delta": -10, "source": "fireball"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["current_hp"] == 28

    # Heal 30 HP: clamps to max_hp (44)
    res = client.post(
        f"/api/v1/characters/{char_id}/health",
        json={"delta": 30, "source": "cure_wounds"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["current_hp"] == 44

    # Detail query reflects updated HP
    detail = client.get(f"/api/v1/characters/{char_id}", headers=headers).json()
    assert detail["current_hp"] == 44
    assert detail["currentHp"] == 44


@pytest.mark.asyncio
async def test_stand_in_permadeath_safeguard_stabilization():
    """Verify that when an AI stand-in character drops to <= 0 HP, safeguard stabilizes them."""
    char_id = create_test_character(owner_id="user_valeros", is_stand_in=True)
    headers = {"X-User-Id": "user_valeros"}

    # Take massive damage dropping HP to <= 0
    res = client.post(
        f"/api/v1/characters/{char_id}/health",
        json={"delta": -100, "source": "dragon_breath"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["current_hp"] == 0
    assert data["is_stabilized"] is True

    # Stand-in receives unconscious_stabilized condition
    conditions = data["conditions"]
    assert "unconscious_stabilized" in conditions


@pytest.mark.asyncio
async def test_equipment_equip_and_unequip():
    """Verify equipping and unequipping items via sub-resource endpoints."""
    char_id = create_test_character()
    headers = {"X-User-Id": "user_valeros"}

    # Equip Longsword to main_hand
    res = client.post(
        f"/api/v1/characters/{char_id}/equipment",
        json={"slot": "main_hand", "item_name": "Flame Tongue Longsword"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["equipment"]["main_hand"] == "Flame Tongue Longsword"

    # Equip Shield to off_hand
    res = client.post(
        f"/api/v1/characters/{char_id}/equipment",
        json={"slot": "off_hand", "item_name": "Shield +1"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["equipment"]["off_hand"] == "Shield +1"

    # Unequip main_hand
    res = client.delete(
        f"/api/v1/characters/{char_id}/equipment/main_hand",
        headers=headers,
    )
    assert res.status_code == 200
    assert "main_hand" not in res.json()["equipment"]
    assert res.json()["equipment"]["off_hand"] == "Shield +1"


@pytest.mark.asyncio
async def test_inventory_add_and_remove():
    """Verify adding and removing inventory items via sub-resource endpoints."""
    char_id = create_test_character()
    headers = {"X-User-Id": "user_valeros"}

    # Add Potion of Healing
    res = client.post(
        f"/api/v1/characters/{char_id}/inventory",
        json={
            "item_id": "item-potion-heal",
            "name": "Potion of Healing",
            "quantity": 3,
            "weight_lbs": 0.5,
        },
        headers=headers,
    )
    assert res.status_code == 200
    inv = res.json()["inventory"]
    assert "item-potion-heal" in inv
    assert inv["item-potion-heal"]["quantity"] == 3

    # Add 1 more potion with same item_id -> quantity increases to 4
    res = client.post(
        f"/api/v1/characters/{char_id}/inventory",
        json={
            "item_id": "item-potion-heal",
            "name": "Potion of Healing",
            "quantity": 1,
            "weight_lbs": 0.5,
        },
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["inventory"]["item-potion-heal"]["quantity"] == 4

    # Remove 2 potions
    res = client.delete(
        f"/api/v1/characters/{char_id}/inventory/item-potion-heal?quantity=2",
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["inventory"]["item-potion-heal"]["quantity"] == 2

    # Remove remaining potions -> item removed from inventory
    res = client.delete(
        f"/api/v1/characters/{char_id}/inventory/item-potion-heal?quantity=2",
        headers=headers,
    )
    assert res.status_code == 200
    assert "item-potion-heal" not in res.json()["inventory"]


@pytest.mark.asyncio
async def test_conditions_apply_and_remove():
    """Verify applying and removing conditions via sub-resource endpoints."""
    char_id = create_test_character()
    headers = {"X-User-Id": "user_valeros"}

    # Apply poisoned condition
    res = client.post(
        f"/api/v1/characters/{char_id}/conditions",
        json={"condition": "poisoned", "source": "serpent_strike"},
        headers=headers,
    )
    assert res.status_code == 200
    assert "poisoned" in res.json()["conditions"]
    assert res.json()["conditions"]["poisoned"]["source"] == "serpent_strike"

    # Apply stunned condition
    res = client.post(
        f"/api/v1/characters/{char_id}/conditions",
        json={"condition": "stunned", "source": "mind_blast"},
        headers=headers,
    )
    assert res.status_code == 200
    assert "stunned" in res.json()["conditions"]

    # Remove poisoned condition
    res = client.delete(
        f"/api/v1/characters/{char_id}/conditions/poisoned",
        headers=headers,
    )
    assert res.status_code == 200
    assert "poisoned" not in res.json()["conditions"]
    assert "stunned" in res.json()["conditions"]


@pytest.mark.asyncio
async def test_spells_cast_and_prepare():
    """Verify spell casting slot deduction and spell preparation toggles."""
    char_id = create_test_character()
    headers = {"X-User-Id": "user_valeros"}

    # Prepare Fireball
    res = client.post(
        f"/api/v1/characters/{char_id}/spells/prepare",
        json={"spell_name": "Fireball", "is_prepared": True},
        headers=headers,
    )
    assert res.status_code == 200
    assert "Fireball" in res.json()["prepared_spells"]

    # Cast 1st-level spell: slots for tier 1 decreases from 4 to 3
    res = client.post(
        f"/api/v1/characters/{char_id}/spells/cast",
        json={"spell_name": "Magic Missile", "slot_level": 1},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["spell_slots"]["1"] == 3

    # Unprepare Fireball
    res = client.post(
        f"/api/v1/characters/{char_id}/spells/prepare",
        json={"spell_name": "Fireball", "is_prepared": False},
        headers=headers,
    )
    assert res.status_code == 200
    assert "Fireball" not in res.json()["prepared_spells"]

    # Cast spell with tier 9 where slots are 0 -> 400 Bad Request
    res_err = client.post(
        f"/api/v1/characters/{char_id}/spells/cast",
        json={"spell_name": "Wish", "slot_level": 9},
        headers=headers,
    )
    assert res_err.status_code == 400


@pytest.mark.asyncio
async def test_zanzibar_unauthorized_mutation_rejection():
    """Verify non-permitted user is rejected with 403 Forbidden on all sub-resource mutations."""
    char_id = create_test_character(owner_id="user_valeros")
    headers_intruder = {"X-User-Id": "user_intruder"}

    # 403 on health mutation
    res = client.post(
        f"/api/v1/characters/{char_id}/health",
        json={"delta": -5},
        headers=headers_intruder,
    )
    assert res.status_code == 403

    # 403 on equipment mutation
    res = client.post(
        f"/api/v1/characters/{char_id}/equipment",
        json={"slot": "head", "item_name": "Crown of Madness"},
        headers=headers_intruder,
    )
    assert res.status_code == 403

    # 403 on inventory mutation
    res = client.post(
        f"/api/v1/characters/{char_id}/inventory",
        json={"name": "Stolen Dagger", "quantity": 1},
        headers=headers_intruder,
    )
    assert res.status_code == 403

    # 403 on conditions mutation
    res = client.post(
        f"/api/v1/characters/{char_id}/conditions",
        json={"condition": "charmed"},
        headers=headers_intruder,
    )
    assert res.status_code == 403

    # 403 on spell cast
    res = client.post(
        f"/api/v1/characters/{char_id}/spells/cast",
        json={"spell_name": "Wish", "slot_level": 9},
        headers=headers_intruder,
    )
    assert res.status_code == 403
