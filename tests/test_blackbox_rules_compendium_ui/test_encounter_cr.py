"""Blackbox TDD tests for Encounter Builder CR balancing and components.

Governed by ADR-0003, ADR-0004, ADR-0013, and Hard Invariant 7.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_rest_data_binding_encounter_balance(client: TestClient) -> None:
    """Verify encounter balancing delivers thresholds and monster recommendations."""
    payload = {
        "party_levels": [3, 3, 3, 3],
        "target_difficulty": "Medium",
    }
    resp = client.post("/api/v1/compendium/encounters/balance", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert "encounter_id" in data
    assert data["party_size"] == 4
    assert data["target_difficulty"] == "Medium"

    thresholds = data["total_party_xp_threshold"]
    assert thresholds["easy"] == 300
    assert thresholds["medium"] == 600
    assert thresholds["hard"] == 900
    assert thresholds["deadly"] == 1600

    assert len(data["monsters"]) >= 1
    rec = data["monsters"][0]
    for key in ("name", "cr", "xp", "count", "role", "subtotal_xp"):
        assert key in rec

    assert data["adjusted_xp"] > 0
    assert data["multiplier"] >= 1.0
    assert "tactical_summary" in data
