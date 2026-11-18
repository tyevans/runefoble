"""Canonical wire names for worker inventory, NPC relationships, and haggling DM overrides.

Each request field has one wire name. The public routes accept the canonical name.
A retired name is ignored, so it never changes the stored value.

Governed by ADR-0007, ADR-0011, PRD-0024, and Hard Invariant 7 (frontdoor blackbox tests).
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient

from .conftest import setup_campaign_settlement


def _create_establishment(tc: TestClient, sid: str, dm_h: dict[str, str]) -> str:
    res = tc.post(
        f"/api/v1/settlements/{sid}/establishments",
        json={"district_id": "artisan", "category": "commerce", "name": "Canonical Anvil"},
        headers=dm_h,
    )
    assert res.status_code == 201, res.text
    return res.json()["establishment_id"]


def _create_worker(tc: TestClient, eid: str, dm_h: dict[str, str], body: dict) -> str:
    res = tc.post(
        f"/api/v1/establishments/{eid}/workers",
        json={"name": "Torvin", "role": "armorer", "wage": 8} | body,
        headers=dm_h,
    )
    assert res.status_code == 201, res.text
    return res.json()["npc_id"]


def test_shelf_inventory_accepts_canonical_quantity_and_unit_price(
    session_client: TestClient, spicedb: MockSpiceDBClient
) -> None:
    """A worker assigned with `quantity` and `unit_price` stocks that exact quantity and price."""
    _, sid, _, dm_h, _ = setup_campaign_settlement(session_client, spicedb, ["artisan"])
    eid = _create_establishment(session_client, sid, dm_h)
    nid = _create_worker(
        session_client,
        eid,
        dm_h,
        {"shelf_inventory": [{"item_id": "plate", "quantity": 2, "unit_price": 150}]},
    )

    inv = session_client.get(f"/api/v1/npcs/{nid}/inventory", headers=dm_h).json()
    item = inv["shelf_inventory"][0]
    assert item["item_id"] == "plate"
    assert item["quantity"] == 2
    assert item["unit_price"] == 150
    assert "stock" not in item and "price_gp" not in item


def test_shelf_inventory_ignores_retired_stock_and_price_gp_names(
    session_client: TestClient, spicedb: MockSpiceDBClient
) -> None:
    """Retired `stock` and `price_gp` keys do not set quantity or unit price."""
    _, sid, _, dm_h, _ = setup_campaign_settlement(session_client, spicedb, ["artisan"])
    eid = _create_establishment(session_client, sid, dm_h)
    nid = _create_worker(
        session_client,
        eid,
        dm_h,
        {"shelf_inventory": [{"item_id": "plate", "stock": 7, "price_gp": 999}]},
    )

    item = session_client.get(f"/api/v1/npcs/{nid}/inventory/plate", headers=dm_h).json()
    assert item["quantity"] == 1
    assert item["unit_price"] == 10


def test_relationship_accepts_canonical_target_npc_id_and_relation_type(
    session_client: TestClient, spicedb: MockSpiceDBClient
) -> None:
    """Forming a tie with `target_npc_id` and `relation_type` records that tie."""
    _, sid, _, dm_h, _ = setup_campaign_settlement(session_client, spicedb, ["artisan"])
    eid = _create_establishment(session_client, sid, dm_h)
    nid = _create_worker(session_client, eid, dm_h, {})

    res = session_client.post(
        f"/api/v1/npcs/{nid}/relationships",
        json={"target_npc_id": "leo", "relation_type": "mentor", "intensity": 0.8},
        headers=dm_h,
    )
    assert res.status_code == 201, res.text

    rels = session_client.get(f"/api/v1/npcs/{nid}/relationships", headers=dm_h).json()
    assert {"target_npc_id": "leo", "relation_type": "mentor"}.items() <= rels[0].items()


def test_relationship_ignores_retired_target_npc_and_relation_names(
    session_client: TestClient, spicedb: MockSpiceDBClient
) -> None:
    """Retired `target_npc` and `relation` keys do not record a tie to the named NPC."""
    _, sid, _, dm_h, _ = setup_campaign_settlement(session_client, spicedb, ["artisan"])
    eid = _create_establishment(session_client, sid, dm_h)
    nid = _create_worker(session_client, eid, dm_h, {})

    session_client.post(
        f"/api/v1/npcs/{nid}/relationships",
        json={"target_npc": "leo", "relation": "mentor", "intensity": 0.8},
        headers=dm_h,
    )

    rels = session_client.get(f"/api/v1/npcs/{nid}/relationships", headers=dm_h).json()
    assert not any(r["target_npc_id"] == "leo" for r in rels)
    assert not any(r["relation_type"] == "mentor" for r in rels)


def test_haggling_dm_override_ignores_retired_override_price_name(
    session_client: TestClient, spicedb: MockSpiceDBClient
) -> None:
    """Only `override_price_gp` sets the forced price. Retired `override_price` is ignored."""
    cid, sid, p_id, dm_h, p_h = setup_campaign_settlement(session_client, spicedb, ["artisan"])
    eid = _create_establishment(session_client, sid, dm_h)
    haggle = session_client.post(
        f"/api/v1/establishments/{eid}/haggle",
        json={
            "character_id": "char_alys",
            "item_id": "blade",
            "item_name": "Blade",
            "base_price": 350,
            "initial_offer_gp": 260,
            "campaign_id": cid,
        },
        headers=p_h,
    ).json()
    neg_id = haggle["negotiation_id"]

    accept = session_client.patch(
        f"/api/v1/haggling/{neg_id}/dm-override",
        json={"action": "force_accept", "override_price": 90},
        headers=dm_h,
    )
    assert accept.status_code == 200, accept.text
    assert accept.json()["status"] == "completed"
    assert accept.json()["counter_price"] != 90


def test_haggling_dm_override_accepts_canonical_override_price_gp(
    session_client: TestClient, spicedb: MockSpiceDBClient
) -> None:
    """`override_price_gp` sets the forced price on a DM accept."""
    cid, sid, _, dm_h, p_h = setup_campaign_settlement(session_client, spicedb, ["artisan"])
    eid = _create_establishment(session_client, sid, dm_h)
    neg_id = session_client.post(
        f"/api/v1/establishments/{eid}/haggle",
        json={
            "character_id": "char_alys",
            "item_id": "blade",
            "item_name": "Blade",
            "base_price": 350,
            "initial_offer_gp": 260,
            "campaign_id": cid,
        },
        headers=p_h,
    ).json()["negotiation_id"]

    accept = session_client.patch(
        f"/api/v1/haggling/{neg_id}/dm-override",
        json={"action": "force_accept", "override_price_gp": 275},
        headers=dm_h,
    )
    assert accept.status_code == 200, accept.text
    assert accept.json()["counter_price"] == 275
