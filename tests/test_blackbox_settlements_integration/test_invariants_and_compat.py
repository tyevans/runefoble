"""Line invariant verifications, backwards compatibility, and modular worker endpoints."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.mark.asyncio
async def test_frontdoor_worker_modular_endpoints(
    session_client: TestClient, spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
):
    """Verify frontdoor execution across roster, relationships, rumors, and shelf inventory routers."""
    cid, gm_id = str(uuid4()), "gm_w"
    await spicedb.write_relationship("campaign", cid, "dungeon_master", "user", gm_id)
    await spicedb.write_relationship("campaign", cid, "player", "user", gm_id)
    h = {"Authorization": f"Bearer {SIGNING_ISSUER.mint(gm_id)}"}

    s_res = session_client.post(
        f"/api/v1/campaigns/{cid}/settlements", json={"name": "WP", "districts": ["m"]}, headers=h
    )
    sid = s_res.json()["settlement_id"]
    e_res = session_client.post(
        f"/api/v1/settlements/{sid}/establishments",
        json={"district_id": "m", "category": "commerce", "name": "Alchemy Haven"},
        headers=h,
    )
    eid = e_res.json()["establishment_id"]

    w_data = {
        "name": "Alchemist Sarah",
        "role": "apothecary",
        "wage": 5,
        "shelf_inventory": [{"item_id": "healing_pot", "stock": 5, "price_gp": 25}],
        "relationships": [{"target_npc": "pip", "relation": "rival", "notes": "Disputed"}],
        "metadata": {"grievance": "overdue"},
        "vault_inventory": [
            {"item_id": "lotus", "stock": 1, "price_gp": 200, "is_contraband": True}
        ],
    }
    nid = session_client.post(
        f"/api/v1/establishments/{eid}/workers", json=w_data, headers=h
    ).json()["npc_id"]

    assert session_client.get(f"/api/v1/npcs/{nid}", headers=h).json()["name"] == "Alchemist Sarah"
    inv = session_client.get(f"/api/v1/npcs/{nid}/inventory", headers=h).json()
    assert inv["total_shelf_items"] == 1 and inv["shelf_inventory"][0]["item_id"] == "healing_pot"
    assert len(session_client.get(f"/api/v1/npcs/{nid}/inventory/vault", headers=h).json()) == 1

    item = session_client.get(f"/api/v1/npcs/{nid}/inventory/healing_pot", headers=h).json()
    assert item.get("price_gp") == 25 or item.get("unit_price") == 25

    restock = session_client.post(
        f"/api/v1/npcs/{nid}/inventory/restock?destination=shelf",
        json={"item_id": "mana_potion", "quantity": 3, "unit_price": 40},
        headers=h,
    )
    assert restock.status_code == 200
    assert restock.json().get("stock") == 3 or restock.json().get("quantity") == 3

    rel = session_client.get(f"/api/v1/npcs/{nid}/relationships", headers=h).json()
    assert len(rel) == 1 and (
        rel[0].get("target_npc_id") == "pip" or rel[0].get("target_npc") == "pip"
    )
    rumors = session_client.get(f"/api/v1/npcs/{nid}/rumors", headers=h).json()
    assert any(r["topic"] == "rival" for r in rumors) and any(
        r["topic"] == "grievance" for r in rumors
    )

    rel_out = session_client.post(
        f"/api/v1/establishments/{eid}/workers/{nid}/relieve", json={"reason": "Done"}, headers=h
    )
    assert rel_out.status_code == 200 and rel_out.json()["status"] == "relieved"
