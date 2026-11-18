"""Blackbox tests for alchemical recipe discovery, potion synthesis, and gateway authorization.

Governed by ADR-0003, ADR-0006, ADR-0007, ADR-0011, and Hard Invariant 7.
"""

from __future__ import annotations

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


def _bearer(issuer, sub: str) -> dict[str, str]:
    """Return Bearer headers carrying a token that the gateway verifies for `sub`."""
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


def test_blackbox_gateway_zanzibar_authorization(
    character_sheet_upstream, gateway_client: TestClient, spicedb, trusted_ws_issuer
):
    """Verify Gateway Zanzibar authorization enforcement for downtime and crafting endpoints.

    Membership is created through frontdoors only: the owner creates the campaign,
    issues a player invite, and the player redeems it.
    """
    owner_headers = _bearer(trusted_ws_issuer, "user_dm")
    user_headers = _bearer(trusted_ws_issuer, "user_bram")

    create_res = gateway_client.post(
        "/api/v1/campaigns",
        json={"title": "Campfire Crafting", "setting": "Ashen Hollow", "system": "5e"},
        headers=owner_headers,
    )
    assert create_res.status_code == 201
    camp_id = create_res.json()["id"]

    invite_res = gateway_client.post(
        f"/api/v1/campaigns/{camp_id}/invites",
        json={"role": "player"},
        headers=owner_headers,
    )
    assert invite_res.status_code == 201
    join_res = gateway_client.post(
        "/api/v1/campaigns/join",
        json={"invite_token": invite_res.json()["token"]},
        headers=user_headers,
    )
    assert join_res.status_code == 200

    get_res = gateway_client.get(f"/api/v1/campaigns/{camp_id}/stronghold", headers=user_headers)
    assert get_res.status_code == 200
    assert get_res.json()["campaign_id"] == camp_id

    denied_res = gateway_client.get(
        f"/api/v1/campaigns/{camp_id}/stronghold",
        headers=_bearer(trusted_ws_issuer, "unauthorized_stranger"),
    )
    assert denied_res.status_code == 403

    funded = gateway_client.post(
        f"/api/v1/campaigns/{camp_id}/stronghold/deposit",
        json={"gold": 100, "materials": {"wood": 20}},
        headers=owner_headers,
    )
    assert funded.status_code == 200, funded.text
    upg_res = gateway_client.post(
        f"/api/v1/campaigns/{camp_id}/stronghold/upgrade",
        json={"facility_id": "watchtower"},
        headers=user_headers,
    )
    assert upg_res.status_code == 200
    assert upg_res.json()["new_tier"] == 1

    char_res = gateway_client.post(
        "/api/v1/characters",
        json={"name": "Bram the Tinkerer", "character_class": "Artificer", "max_hp": 24},
        headers=user_headers,
    )
    assert char_res.status_code == 201, char_res.text
    craft_res = gateway_client.post(
        "/api/v1/crafting/recipes/combine",
        json={
            "character_id": char_res.json()["id"],
            "reagents": ["Glowmoss Extract", "Volcano Ash"],
            "catalyst": "purified_water",
        },
        headers=user_headers,
    )
    assert craft_res.status_code == 200, craft_res.text
    assert craft_res.json()["reagents_consumed"] == ["Glowmoss Extract", "Volcano Ash"]
