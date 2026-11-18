"""Blackbox tests for Campfire Crafting Subviews Modular Decomposition.

TASK-0199: Campfire Crafting Subviews Modular Decomposition
Governed by ADR-0004, ADR-0007, ADR-0012, ADR-0013, and Hard Invariants 6 & 7.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from game_session.events import STREAM_SESSION, STREAM_STRONGHOLD


def _owned_campaign(client: TestClient) -> str:
    """Create a campaign through the public route. The caller becomes its owner."""
    created = client.post("/api/v1/campaigns", json={"title": "Campfire Campaign"})
    assert created.status_code == 201, created.text
    return created.json()["id"]


def test_blackbox_campfire_crafting_frontdoor_integration(
    session_client: TestClient, char_client: TestClient, mock_bus
) -> None:
    """Verify campfire rest and alchemical crafting workflows via public frontdoors."""
    camp_id = _owned_campaign(session_client)
    session_res = session_client.post(
        "/api/v1/sessions/create",
        json={
            "campaign_id": _owned_campaign(session_client),
            "title": "Campfire Haven Session",
            "dm_id": "dm_bram",
        },
    )
    assert session_res.status_code == 200
    session_id = session_res.json()["session_id"]

    funded = session_client.post(
        f"/api/v1/campaigns/{camp_id}/stronghold/deposit",
        json={"gold": 100, "materials": {"wood": 20}},
    )
    assert funded.status_code == 200, funded.text
    upg_res = session_client.post(
        f"/api/v1/campaigns/{camp_id}/stronghold/upgrade",
        json={"facility_id": "watchtower"},
    )
    assert upg_res.status_code == 200 and upg_res.json()["new_tier"] == 1

    rest_res = session_client.post(
        f"/api/v1/sessions/{session_id}/rest/campfire",
        json={"rest_type": "long", "storytelling_prompt": "First monster that frightened you."},
    )
    assert rest_res.status_code == 200 and rest_res.json()["status"] == "completed"

    session_entries = mock_bus.streams.get(STREAM_SESSION, [])
    assert any("CampfireRestCompleted" in e[1].get("event_type", "") for e in session_entries)
    stronghold_entries = mock_bus.streams.get(STREAM_STRONGHOLD, [])
    assert any("StrongholdUpgraded" in e[1].get("event_type", "") for e in stronghold_entries)

    char_res = char_client.post(
        "/api/v1/characters",
        json={"name": "Bram Master Alchemist", "character_class": "Artificer", "max_hp": 26},
    )
    assert char_res.status_code == 200
    char_id = char_res.json()["character_id"]

    combine_res = char_client.post(
        "/api/v1/crafting/recipes/combine",
        json={
            "character_id": char_id,
            "reagents": ["Glowmoss Extract", "Volcano Ash"],
            "catalyst": "purified_water",
        },
    )
    assert combine_res.status_code == 200
    data = combine_res.json()
    assert data["outcome"] == "success" and data["item_name"] == "Radiant Smoke Pellet"


def _owned_campaign(client) -> str:
    """Create a campaign as the calling user, so that the caller can run sessions in it."""
    res = client.post("/api/v1/campaigns", json={"title": "Owned Campaign"})
    assert res.status_code == 201, res.text
    return res.json()["id"]
