"""Settlement founding, tier upgrades, establishment creation, and NPC worker assignments."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session.events import STREAM_WEST_MARCHES
from runefoble_auth.mock import MockSpiceDBClient

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.stream_events import assert_stream_events
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


def test_found_settlement_and_upgrade_tier_flow(
    session_client: TestClient, spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
) -> None:
    """Found settlement, verify district slot caps per scale, and upgrade civic tier."""
    cid, mayor_id = str(uuid4()), "mayor_1"
    h = {"Authorization": f"Bearer {SIGNING_ISSUER.mint(mayor_id)}"}
    asyncio.run(spicedb.write_relationship("campaign", cid, "dungeon_master", "user", mayor_id))
    asyncio.run(spicedb.write_relationship("campaign", cid, "player", "user", mayor_id))

    url = f"/api/v1/campaigns/{cid}/settlements"
    bad = session_client.post(
        url, json={"name": "X", "scale": "hamlet", "districts": ["1", "2", "3"]}, headers=h
    )
    assert bad.status_code == 400 and "permits at most 2 districts" in bad.json()["detail"]

    found = session_client.post(
        url, json={"name": "Oak Crossing", "scale": "hamlet", "districts": ["c", "r"]}, headers=h
    )
    assert found.status_code == 201
    sid = found.json()["settlement_id"]
    assert found.json()["scale"] == "hamlet" and found.json()["tier"] == 1
    assert_stream_events(mock_bus, "SettlementFounded", stream=STREAM_WEST_MARCHES)

    assert session_client.get(f"{url}/{sid}", headers=h).status_code == 200

    upg_url = f"/api/v1/settlements/{sid}/upgrade-tier"
    fail = session_client.post(upg_url, json={"new_tier": 2, "prosperity": 60}, headers=h)
    assert fail.status_code == 400 and "Insufficient civic prosperity" in fail.json()["detail"]

    upg = session_client.post(upg_url, json={"new_tier": 2, "prosperity": 150}, headers=h)
    assert upg.status_code == 200
    u = upg.json()
    assert u["tier"] == 2 and u["scale"] == "village" and u["max_districts"] == 4
    assert "defensive_palisade" in u["districts"]
    assert_stream_events(mock_bus, "SettlementTierUpgraded", stream=STREAM_WEST_MARCHES)


def test_establishment_creation_and_worker_assignment(
    session_client: TestClient, spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
) -> None:
    """Place weaponsmith establishment, assign NPC armorer, and verify dynamic inventory."""
    cid, dm_id = str(uuid4()), f"dm_{uuid4().hex[:8]}"
    h = {"Authorization": f"Bearer {SIGNING_ISSUER.mint(dm_id)}"}
    asyncio.run(spicedb.write_relationship("campaign", cid, "dungeon_master", "user", dm_id))
    asyncio.run(spicedb.write_relationship("campaign", cid, "player", "user", dm_id))

    s_res = session_client.post(
        f"/api/v1/campaigns/{cid}/settlements",
        json={"name": "Ironhaven", "scale": "village", "districts": ["artisan_quarter"]},
        headers=h,
    )
    sid = s_res.json()["settlement_id"]

    est_res = session_client.post(
        f"/api/v1/settlements/{sid}/establishments",
        json={"district_id": "artisan_quarter", "category": "commerce", "name": "The Ember Anvil"},
        headers=h,
    )
    assert est_res.status_code == 201
    eid = est_res.json()["establishment_id"]
    assert_stream_events(mock_bus, "EstablishmentConstructed", stream=STREAM_WEST_MARCHES)

    def _inv(i: str, s: int, p: int) -> dict:
        return {"item_id": i, "quantity": s, "unit_price": p}

    worker_payload = {
        "name": "Korgan Deepforge",
        "role": "armorer",
        "wage": 10,
        "trade_proficiencies": ["blacksmithing", "armorer"],
        "shelf_inventory": [_inv("blade_adamantine", 3, 350), _inv("plate_armor", 1, 1500)],
        "vault_inventory": [_inv("iron_ingots", 40, 5)],
        "temperament": "Stubborn",
        "patience": 5,
    }
    worker_res = session_client.post(
        f"/api/v1/establishments/{eid}/workers", json=worker_payload, headers=h
    )
    assert worker_res.status_code == 201
    worker = worker_res.json()
    assert worker["role"] == "armorer" and worker["service_quality_contribution"] > 1.2
    assert_stream_events(mock_bus, "NPCWorkerAssigned", stream=STREAM_WEST_MARCHES)

    roster = session_client.get(f"/api/v1/establishments/{eid}/workers", headers=h).json()
    assert len(roster) == 1
    shelf_items = [i["item_id"] for i in roster[0]["shelf_inventory"]]
    assert "blade_adamantine" in shelf_items and "plate_armor" in shelf_items
    assert len(roster[0]["backroom_inventory"]) == 1
