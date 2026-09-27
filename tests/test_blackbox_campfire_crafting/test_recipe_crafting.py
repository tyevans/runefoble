"""Blackbox tests for alchemical recipe discovery, potion synthesis, and gateway authorization.

Governed by ADR-0003, ADR-0006, ADR-0007, ADR-0011, and Hard Invariant 7.
"""

from __future__ import annotations

from uuid import uuid4

from character_sheet.dependencies import STREAM_CRAFTING
from fastapi.testclient import TestClient


def test_blackbox_reagent_recipes_and_catalogue(char_client: TestClient):
    """Verify public query endpoints for reagents, affinities, and known recipes."""
    rec_res = char_client.get("/api/v1/crafting/recipes")
    assert rec_res.status_code == 200
    recipes = rec_res.json()
    recipe_names = [r["name"] for r in recipes]
    assert "Radiant Smoke Pellet" in recipe_names
    assert "Elixir of Luminescence" in recipe_names

    reag_res = char_client.get("/api/v1/crafting/reagents")
    assert reag_res.status_code == 200
    reag_data = reag_res.json()
    assert "Glowmoss Extract" in reag_data["reagents"]
    assert "Volcano Ash" in reag_data["reagents"]
    assert "purified_water" in reag_data["catalysts"]


def test_blackbox_alchemical_crafting_success_flow(char_client: TestClient, mock_bus):
    """Test reagent combination success generating novel item and updating inventory."""
    create_res = char_client.post(
        "/api/v1/characters",
        json={"name": "Bram the Tinkerer", "character_class": "Artificer", "max_hp": 24},
    )
    assert create_res.status_code == 200
    char_id = create_res.json()["character_id"]

    char_client.post(
        f"/api/v1/characters/{char_id}/inventory/add",
        json={"name": "Glowmoss Extract", "quantity": 1, "weight_lbs": 0.2},
    )
    char_client.post(
        f"/api/v1/characters/{char_id}/inventory/add",
        json={"name": "Volcano Ash", "quantity": 1, "weight_lbs": 0.5},
    )

    combine_payload = {
        "character_id": char_id,
        "reagents": ["Glowmoss Extract", "Volcano Ash"],
        "catalyst": "purified_water",
    }
    combine_res = char_client.post("/api/v1/crafting/recipes/combine", json=combine_payload)
    assert combine_res.status_code == 200, combine_res.text
    result = combine_res.json()

    assert result["outcome"] == "success"
    assert result["item_name"] == "Radiant Smoke Pellet"
    assert "radiant" in result["tags"]
    assert "obscurement" in result["tags"]

    char_res = char_client.get(f"/api/v1/characters/{char_id}")
    assert char_res.status_code == 200
    char_data = char_res.json()
    inv_names = [i["name"] for i in char_data["inventory"].values()]
    assert "Radiant Smoke Pellet" in inv_names

    hist_res = char_client.get(f"/api/v1/crafting/{char_id}/history")
    assert hist_res.status_code == 200
    hist = hist_res.json()
    assert hist["total_crafts"] >= 1
    assert hist["successful_crafts"] >= 1
    assert "Radiant Smoke Pellet" in hist["discovered_recipes"]

    entries = mock_bus.streams.get(STREAM_CRAFTING, [])
    assert any("CraftingAttempted" in entry[1].get("event_type", "") for entry in entries)
    assert any("CraftingSucceeded" in entry[1].get("event_type", "") for entry in entries)


def test_blackbox_gateway_zanzibar_authorization(gateway_client: TestClient, mock_spicedb):
    """Verify Gateway Zanzibar authorization enforcement for downtime and crafting endpoints."""
    camp_id = f"camp-auth-{uuid4().hex[:6]}"
    user_id = "user_bram"

    role_res = gateway_client.post(
        f"/api/v1/campaigns/{camp_id}/roles",
        json={"user_id": user_id, "role": "player"},
    )
    assert role_res.status_code == 200

    get_res = gateway_client.get(
        f"/api/v1/campaigns/{camp_id}/stronghold",
        headers={"X-User-Id": user_id},
    )
    assert get_res.status_code == 200
    assert get_res.json()["campaign_id"] == camp_id

    denied_res = gateway_client.get(
        f"/api/v1/campaigns/{camp_id}/stronghold",
        headers={"X-User-Id": "unauthorized_stranger"},
    )
    assert denied_res.status_code == 403

    upg_res = gateway_client.post(
        f"/api/v1/campaigns/{camp_id}/stronghold/upgrade",
        json={"facility_id": "watchtower", "gold_spent": 100},
        headers={"X-User-Id": user_id},
    )
    assert upg_res.status_code == 200
    assert upg_res.json()["status"] == "upgraded"

    craft_res = gateway_client.post(
        "/api/v1/crafting/recipes/combine",
        json={
            "character_id": str(uuid4()),
            "reagents": ["Glowmoss Extract", "Volcano Ash"],
        },
        headers={"X-User-Id": user_id},
        params={"campaign_id": camp_id},
    )
    assert craft_res.status_code == 200
    assert craft_res.json()["item_name"] == "Radiant Smoke Pellet"
