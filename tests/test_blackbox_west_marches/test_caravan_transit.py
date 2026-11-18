"""Blackbox tests for West Marches caravan logistics and regional merchant trade.

Governed by ADR-0001, ADR-0006, and Hard Invariant 7 (Blackbox TDD).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from game_session.events import STREAM_WEST_MARCHES
from runefoble_auth.spicedb import MockSpiceDBClient

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


async def _setup_world(
    client: TestClient,
    spicedb: MockSpiceDBClient,
    officer: str,
    parties: list[tuple[str, str, str]],
) -> str:
    res = client.post(
        "/api/v1/shared-worlds",
        json={"name": "The Sunken Marches", "frontier_region": "Trade Coast"},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(officer)}"},
    )
    wid = res.json()["shared_world_id"]
    for cid, _uid, pname in parties:
        client.post(
            f"/api/v1/shared-worlds/{wid}/campaigns",
            json={"campaign_id": cid, "party_name": pname},
            headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(officer)}"},
        )
    return wid


@pytest.mark.asyncio
async def test_blackbox_caravan_trade_and_merchant_stock_unlocks(
    client: TestClient,
    mock_bus: MockAsyncRedis,
    spicedb: MockSpiceDBClient,
    party_ids: dict[str, str],
):
    """Test Scenario 2 (US-0058): Caravan Trading and Outpost Resource Ledgers."""
    officer_id = party_ids["officer"]
    blue_trader, gold_buyer = party_ids["blue_player"], party_ids["gold_player"]
    c_blue, c_gold = party_ids["campaign_blue"], party_ids["campaign_gold"]

    world_id = await _setup_world(
        client,
        spicedb,
        officer_id,
        [(c_blue, blue_trader, "Party Blue"), (c_gold, gold_buyer, "Party Gold")],
    )

    outpost = client.post(
        f"/api/v1/shared-worlds/{world_id}/outposts",
        json={
            "name": "Highport",
            "region": "Coast",
            "contributing_campaign_id": c_blue,
            "facilities": {"harbor": 1},
        },
        headers={
            "Authorization": f"Bearer {SIGNING_ISSUER.mint(officer_id)}"
        },  # outposts need manage
    )
    assert outpost.status_code == 201

    cargo = {"alchemical_reagents": 10, "silver_bloom": 5}
    d_res = client.post(
        f"/api/v1/shared-worlds/{world_id}/caravans/dispatch",
        json={
            "origin_outpost": "Fort Rowan",
            "destination_outpost": "Highport",
            "cargo": cargo,
            "dispatched_by_campaign_id": c_blue,
            "transit_turns": 2,
        },
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(blue_trader)}"},
    )
    assert d_res.status_code == 201
    caravan_id = d_res.json()["caravan"]["caravan_id"]
    assert d_res.json()["caravan"]["status"] == "in_transit"

    elixir = {"name": "Elixir of Frost", "price_gold": 50, "quantity": 6, "rarity": "rare"}
    complete_res = client.post(
        f"/api/v1/shared-worlds/{world_id}/caravans/{caravan_id}/complete",
        json={"unlocked_stock": {"elixir_of_frost_resistance": elixir}},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(blue_trader)}"},
    )
    assert complete_res.status_code == 200
    assert complete_res.json()["caravan"]["status"] == "completed"

    entries = mock_bus.streams.get(STREAM_WEST_MARCHES, [])
    assert any("CaravanTradeCompleted" in str(entry[1]) for entry in entries)

    stock = client.get(
        f"/api/v1/shared-worlds/{world_id}/outposts/Highport/merchant-stock",
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(gold_buyer)}"},
    ).json()["stock"]
    assert stock["workshop_reagents"]["alchemical_reagents"] == 10
    assert stock["workshop_reagents"]["silver_bloom"] == 5
    assert "elixir_of_frost_resistance" in stock["inventory"]
    assert stock["inventory"]["elixir_of_frost_resistance"]["rarity"] == "rare"


@pytest.mark.asyncio
async def test_caravan_completion_not_found(client: TestClient, party_ids: dict[str, str]):
    """Verify completing a non-existent caravan returns 404."""
    officer_id = party_ids["officer"]
    world_res = client.post(
        "/api/v1/shared-worlds",
        json={"name": "Barrow Downs"},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(officer_id)}"},
    )
    world_id = world_res.json()["shared_world_id"]

    res = client.post(
        f"/api/v1/shared-worlds/{world_id}/caravans/missing-id/complete",
        json={"unlocked_stock": {}},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(officer_id)}"},
    )
    assert res.status_code == 404
