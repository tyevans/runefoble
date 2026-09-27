"""Blackbox tests for alchemical volatile mishaps, explosion events, and setback conditions.

Governed by ADR-0003, ADR-0006, ADR-0007, ADR-0011, and Hard Invariant 7.
"""

from __future__ import annotations

from character_sheet.dependencies import STREAM_CRAFTING
from fastapi.testclient import TestClient


def test_blackbox_alchemical_crafting_volatile_mishap(char_client: TestClient, mock_bus):
    """Test volatile reaction mishap triggering damage and condition."""
    create_res = char_client.post(
        "/api/v1/characters",
        json={"name": "Novice Apprentice", "character_class": "Wizard", "max_hp": 16},
    )
    assert create_res.status_code == 200
    char_id = create_res.json()["character_id"]
    initial_hp = create_res.json()["current_hp"]

    mishap_payload = {
        "character_id": char_id,
        "reagents": ["Volcano Ash", "Wyrm Blood"],
        "force_mishap": True,
    }
    combine_res = char_client.post("/api/v1/crafting/recipes/combine", json=mishap_payload)
    assert combine_res.status_code == 200
    result = combine_res.json()

    assert result["outcome"] == "mishap"
    assert result["mishap"] is not None
    assert result["character_current_hp"] < initial_hp

    char_res = char_client.get(f"/api/v1/characters/{char_id}")
    assert char_res.json()["current_hp"] == result["character_current_hp"]

    entries = mock_bus.streams.get(STREAM_CRAFTING, [])
    assert any("CraftingMishapOccurred" in entry[1].get("event_type", "") for entry in entries)


def test_blackbox_volatile_mishap_threshold_and_setback(char_client: TestClient, mock_bus):
    """Test failure thresholds, volatile explosion events, and setback condition effects."""
    create_res = char_client.post(
        "/api/v1/characters",
        json={"name": "Pyromancer Ignis", "character_class": "Sorcerer", "max_hp": 20},
    )
    assert create_res.status_code == 200
    char_id = create_res.json()["character_id"]

    payload = {
        "character_id": char_id,
        "reagents": ["Volcano Ash", "Wyrm Blood"],
        "risk_threshold": 0.05,
    }
    res = char_client.post("/api/v1/crafting/recipes/combine", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["outcome"] == "mishap"
    assert data["mishap"] is not None
    assert data["risk_score"] > 0.05
    assert data["character_current_hp"] < 20

    char_res = char_client.get(f"/api/v1/characters/{char_id}")
    assert char_res.status_code == 200
    char_data = char_res.json()
    if data["mishap"].get("condition"):
        assert data["mishap"]["condition"] in char_data["conditions"]

    entries = mock_bus.streams.get(STREAM_CRAFTING, [])
    mishap_events = [e for e in entries if "CraftingMishapOccurred" in e[1].get("event_type", "")]
    assert len(mishap_events) >= 1
