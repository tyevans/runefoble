"""Tests for faction skirmishes, tactical modifiers, casualties, and outcome resolution.

Governed by ADR-0002, ADR-0007, and Hard Invariant 7 (Blackbox TDD).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from .conftest import setup_campaign_roles


@pytest.mark.asyncio
async def test_skirmish_simulation_attacker_victory(client: TestClient):
    """Verify tactical modifiers, casualties, and attacker victory resolution."""
    camp_id, dm_user, _ = await setup_campaign_roles()
    region_id = f"reg-{uuid4().hex[:8]}"

    payload = {
        "campaign_id": camp_id,
        "region_id": region_id,
        "contested_node": "Smugglers Cove",
        "attacker": {"faction_id": "blood_corsairs", "military_strength": 50, "morale_modifier": 2},
        "defender": {"faction_id": "harbor_militia", "military_strength": 20, "defense_rating": 2},
        "terrain": "plains",
        "attacker_roll": 18,
        "defender_roll": 4,
    }

    res = client.post(
        "/the-watcher/factions/skirmish/simulate",
        json=payload,
        headers={"X-User-Id": dm_user},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["winner_faction_id"] == "blood_corsairs"
    assert data["loser_faction_id"] == "harbor_militia"
    assert data["territory_captured"] is True
    assert data["defender_casualties"] > 5
    assert data["unrest_delta"] > 10


@pytest.mark.asyncio
async def test_skirmish_simulation_defender_hold_terrain_advantage(client: TestClient):
    """Verify defender with strong fortification advantage repels attackers."""
    camp_id, dm_user, _ = await setup_campaign_roles()
    region_id = f"reg-{uuid4().hex[:8]}"

    payload = {
        "campaign_id": camp_id,
        "region_id": region_id,
        "contested_node": "High Stone Citadel",
        "attacker": {"faction_id": "goblin_horde", "military_strength": 25},
        "defender": {"faction_id": "dwarf_legion", "military_strength": 30, "defense_rating": 5},
        "terrain": "fortress",
        "attacker_roll": 5,
        "defender_roll": 16,
    }

    res = client.post(
        "/the-watcher/factions/skirmish/simulate",
        json=payload,
        headers={"X-User-Id": dm_user},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["winner_faction_id"] == "dwarf_legion"
    assert data["loser_faction_id"] == "goblin_horde"
    assert data["territory_captured"] is False
    assert data["attacker_casualties"] > data["defender_casualties"]


@pytest.mark.asyncio
async def test_skirmish_stalemate_resolution(client: TestClient):
    """Verify equal strength and rolls result in a bloody stalemate."""
    camp_id, dm_user, _ = await setup_campaign_roles()
    region_id = f"reg-{uuid4().hex[:8]}"

    payload = {
        "campaign_id": camp_id,
        "region_id": region_id,
        "contested_node": "Dead Man Crossroads",
        "attacker": {"faction_id": "guild_a", "military_strength": 20},
        "defender": {"faction_id": "guild_b", "military_strength": 20, "defense_rating": 0},
        "terrain": "plains",
        "attacker_roll": 10,
        "defender_roll": 10,
    }

    res = client.post(
        "/the-watcher/factions/skirmish/simulate",
        json=payload,
        headers={"X-User-Id": dm_user},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_stalemate"] is True
    assert data["territory_captured"] is False
    assert "stalemate" in data["narrative"].lower()
