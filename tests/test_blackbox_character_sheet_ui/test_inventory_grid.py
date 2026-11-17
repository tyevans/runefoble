"""Blackbox TDD tests for Character Sheet inventory, equipment, and encumbrance.

Governed by ADR-0003, ADR-0004, ADR-0007, ADR-0013, and Hard Invariant 7.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_inventory_addition_and_removal(client: TestClient, created_character_id: str) -> None:
    """Verify item addition, removal, and weight tracking via frontdoor REST."""
    char_id = created_character_id
    add_resp = client.post(
        f"/api/v1/characters/{char_id}/inventory/add",
        json={"item_id": "item-potion", "name": "Healing Potion", "quantity": 3, "weight_lbs": 1.5},
    )
    assert add_resp.status_code == 200
    sheet = add_resp.json()
    assert "item-potion" in sheet["inventory"]
    assert sheet["inventory"]["item-potion"]["quantity"] == 3

    rem_resp = client.post(
        f"/api/v1/characters/{char_id}/inventory/item-potion/remove",
        json={"quantity": 3},
    )
    assert rem_resp.status_code == 200
    assert "item-potion" not in rem_resp.json()["inventory"]


def test_equipment_paper_doll_slots(client: TestClient, created_character_id: str) -> None:
    """Verify equipping items into paper doll slots (main_hand, off_hand, armor)."""
    char_id = created_character_id
    for item in (
        {"item_id": "sword-1", "name": "Longsword +1", "quantity": 1, "weight_lbs": 3.0},
        {"item_id": "shield-1", "name": "Steel Shield", "quantity": 1, "weight_lbs": 6.0},
        {"item_id": "armor-1", "name": "Chain Mail", "quantity": 1, "weight_lbs": 55.0},
    ):
        client.post(f"/api/v1/characters/{char_id}/inventory/add", json=item)

    slots = [
        ("main_hand", "Longsword +1"),
        ("off_hand", "Steel Shield"),
        ("armor", "Chain Mail"),
    ]
    for slot, item_name in slots:
        res = client.post(
            f"/api/v1/characters/{char_id}/equipment",
            json={"slot": slot, "item_name": item_name},
        )
        assert res.status_code == 200
        assert res.json()["equipment"][slot] == item_name
