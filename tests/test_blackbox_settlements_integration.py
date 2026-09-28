"""Blackbox integration test suite for settlements, modular auth, workers, and haggling (PRD-0024)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import pytest
from fastapi import APIRouter, Depends, HTTPException
from fastapi.testclient import TestClient
from game_session.dependencies import (
    STREAM_TAVERN,
    STREAM_WEST_MARCHES,
)
from game_session.dependencies import (
    set_event_bus as set_session_bus,
)
from game_session.dependencies import (
    set_spicedb_client as set_session_spicedb,
)
from game_session.main import app as session_app
from game_session.settlement import auth as sa
from gateway_api.auth import set_spicedb_client as set_gateway_spicedb
from gateway_api.dependencies import set_event_bus as set_gateway_bus
from gateway_api.main import app as gateway_app
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_auth.zitadel import ZitadelAuthService
from runefoble_platform.mock_redis import MockAsyncRedis
from runefoble_platform.redis_bus import RedisStreamsEventBus


@pytest.fixture
def mock_bus():
    redis_client = MockAsyncRedis()
    bus = RedisStreamsEventBus(client=redis_client)
    set_session_bus(bus)
    set_gateway_bus(bus)
    yield redis_client
    set_session_bus(None)
    set_gateway_bus(None)


@pytest.fixture
def spicedb():
    mock_db = MockSpiceDBClient()
    set_session_spicedb(mock_db)
    set_gateway_spicedb(mock_db)
    yield mock_db
    set_session_spicedb(MockSpiceDBClient())
    set_gateway_spicedb(MockSpiceDBClient())


@pytest.fixture
def session_client(spicedb, mock_bus) -> TestClient:
    return TestClient(session_app)


client = session_client


@pytest.fixture
def gateway_client(spicedb, mock_bus) -> TestClient:
    return TestClient(gateway_app)


@pytest.fixture(autouse=True)
def clean_gateway_ws():
    from gateway_api.websocket_manager import ws_campaign_manager

    ws_campaign_manager.active_connections.clear()
    yield
    ws_campaign_manager.active_connections.clear()


def assert_stream_event(mock_bus: MockAsyncRedis, stream: str, event_name: str) -> None:
    entries = mock_bus.streams.get(stream, [])
    ev_norm = event_name.lower().replace("_", "")
    assert any(ev_norm in str(e[1]).lower().replace("_", "") for e in entries)


def _assert_submodules(dir_path: str, facade_path: str) -> None:
    base, facade = Path(dir_path), Path(facade_path)
    assert base.is_dir() and facade.exists() and len(facade.read_text().splitlines()) < 40
    submodules = list(base.glob("*.py"))
    assert len(submodules) >= 4
    for sm in submodules:
        lines = len(sm.read_text().splitlines())
        assert lines < 130, f"{sm.name} must be strictly < 130 lines, got {lines}"


def test_modular_submodule_line_invariants():
    """Verify extracted auth and worker submodules remain strictly < 130 lines."""
    _assert_submodules(
        "services/game_session/src/game_session/settlement/auth",
        "services/game_session/src/game_session/settlement/auth.py",
    )
    _assert_submodules(
        "services/game_session/src/game_session/settlement/workers",
        "services/game_session/src/game_session/settlement/workers_router.py",
    )


def test_auth_backwards_compatibility_exports():
    """Verify complete backwards compatibility of exported symbols from game_session.settlement.auth."""
    import game_session.settlement.auth as auth_mod

    expected = (  # noqa: SIM905
        "check_campaign_write_permission check_settlement_read_permission "
        "check_settlement_write_permission check_establishment_read_permission "
        "check_establishment_write_permission check_establishment_play_permission "
        "check_npc_read_permission check_npc_write_permission "
        "check_negotiation_read_permission check_negotiation_participate_permission "
        "check_negotiation_arbitrate_permission write_settlement_relationships "
        "write_establishment_relationships write_npc_relationships "
        "write_negotiation_relationships get_current_settlement_user "
        "require_haven_builder require_establishment_manager "
        "extract_bearer_token decode_settlement_token AuthenticatedUser"
    ).split()
    for sym in expected:
        assert hasattr(auth_mod, sym), f"Missing exported symbol {sym} in auth facade"


def test_bearer_token_extraction_and_decoding():
    """Verify Zitadel bearer token extraction and dev mock resolution."""
    assert sa.extract_bearer_token(None) is None
    assert sa.extract_bearer_token("Basic 12345") is None
    assert sa.extract_bearer_token("Bearer secret_jwt_token") == "secret_jwt_token"

    dev_user = sa.decode_settlement_token(authorization=None, x_user_id="artisan_bob")
    assert dev_user.user_id == "artisan_bob" and "player" in dev_user.roles

    service = ZitadelAuthService(dev_mode=False)
    sa.set_zitadel_auth_service(service)
    try:
        with pytest.raises(HTTPException) as exc:
            sa.decode_settlement_token(authorization=None, x_user_id="intruder")
        assert exc.value.status_code == 401
    finally:
        sa.set_zitadel_auth_service(None)


def test_fastapi_route_dependencies(spicedb: MockSpiceDBClient):
    """Verify FastAPI dependency factories enforce Zanzibar object-level permissions."""
    r = APIRouter(prefix="/api/v1/test_auth")

    @r.get("/h/{s}", dependencies=[Depends(sa.require_haven_builder("s"))])
    async def h_ep(u: Annotated[sa.AuthenticatedUser, Depends(sa.get_current_settlement_user)]):
        return {"user": u.user_id}

    @r.get("/e/{e}", dependencies=[Depends(sa.require_establishment_manager("e"))])
    async def e_ep(u: Annotated[sa.AuthenticatedUser, Depends(sa.get_current_settlement_user)]):
        return {"user": u.user_id}

    session_app.include_router(r)
    tc = TestClient(session_app)
    asyncio.run(spicedb.write_relationship("settlement", "h1", "upgrade", "user", "builder"))
    asyncio.run(spicedb.write_relationship("establishment", "e1", "manage", "user", "builder"))

    assert tc.get("/api/v1/test_auth/h/h1", headers={"x-user-id": "builder"}).status_code == 200
    assert tc.get("/api/v1/test_auth/e/e1", headers={"x-user-id": "builder"}).status_code == 200
    assert tc.get("/api/v1/test_auth/h/h1", headers={"x-user-id": "intruder"}).status_code == 403
    assert tc.get("/api/v1/test_auth/e/e1", headers={"x-user-id": "intruder"}).status_code == 403


def test_frontdoor_settlement_auth_lifecycle(client: TestClient, spicedb: MockSpiceDBClient):
    """End-to-end blackbox frontdoor verifying authorization across settlement and establishment endpoints."""
    cid, gm_id, p_id, int_id = str(uuid4()), "gm_1", "p_1", "int_1"
    asyncio.run(spicedb.write_relationship("campaign", cid, "manage", "user", gm_id))
    asyncio.run(spicedb.write_relationship("campaign", cid, "play", "user", p_id))

    url = f"/api/v1/campaigns/{cid}/settlements"
    bad = client.post(
        url, json={"name": "Outlaw Camp", "scale": "hamlet"}, headers={"x-user-id": int_id}
    )
    assert bad.status_code == 403

    ok = client.post(
        url, json={"name": "Garrison Prime", "scale": "village"}, headers={"x-user-id": gm_id}
    )
    assert ok.status_code == 201
    sid = ok.json()["settlement_id"]

    assert client.get(f"{url}/{sid}", headers={"x-user-id": p_id}).status_code == 200
    assert client.get(f"{url}/{sid}", headers={"x-user-id": int_id}).status_code == 403


def test_workers_backwards_compatibility_exports():
    """Verify backwards compatibility of exported symbols from workers_router and workers."""
    import game_session.settlement.workers as workers_pkg
    import game_session.settlement.workers_router as wr_mod

    for sym in ["router", "roster_router", "relationships_router", "inventory_router"]:
        assert hasattr(wr_mod, sym), f"Missing exported symbol {sym} in workers_router"
    expected = (  # noqa: SIM905
        "NPCWorkerAggregate AssignWorkerRequest NPCWorkerState RelieveWorkerRequest "
        "UpdateWorkerMoodRequest WorkerInventoryItem WorkerRelationship"
    ).split()
    for sym in expected:
        assert hasattr(workers_pkg, sym), f"Missing exported symbol {sym} in workers package"


@pytest.mark.asyncio
async def test_frontdoor_worker_modular_endpoints(
    client: TestClient, spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
):
    """Verify frontdoor execution across roster, relationships, rumors, and shelf inventory routers."""
    cid, gm_id = str(uuid4()), "gm_w"
    await spicedb.write_relationship("campaign", cid, "dungeon_master", "user", gm_id)
    await spicedb.write_relationship("campaign", cid, "player", "user", gm_id)
    h = {"x-user-id": gm_id}

    s_res = client.post(
        f"/api/v1/campaigns/{cid}/settlements", json={"name": "WP", "districts": ["m"]}, headers=h
    )
    sid = s_res.json()["settlement_id"]
    e_res = client.post(
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
    nid = client.post(f"/api/v1/establishments/{eid}/workers", json=w_data, headers=h).json()[
        "npc_id"
    ]

    assert client.get(f"/api/v1/npcs/{nid}", headers=h).json()["name"] == "Alchemist Sarah"
    inv = client.get(f"/api/v1/npcs/{nid}/inventory", headers=h).json()
    assert inv["total_shelf_items"] == 1 and inv["shelf_inventory"][0]["item_id"] == "healing_pot"
    assert len(client.get(f"/api/v1/npcs/{nid}/inventory/vault", headers=h).json()) == 1

    item = client.get(f"/api/v1/npcs/{nid}/inventory/healing_pot", headers=h).json()
    assert item.get("price_gp") == 25 or item.get("unit_price") == 25

    restock = client.post(
        f"/api/v1/npcs/{nid}/inventory/restock?destination=shelf",
        json={"item_id": "mana_potion", "quantity": 3, "unit_price": 40},
        headers=h,
    )
    assert restock.status_code == 200
    assert restock.json().get("stock") == 3 or restock.json().get("quantity") == 3

    rel = client.get(f"/api/v1/npcs/{nid}/relationships", headers=h).json()
    assert len(rel) == 1 and (
        rel[0].get("target_npc_id") == "pip" or rel[0].get("target_npc") == "pip"
    )
    rumors = client.get(f"/api/v1/npcs/{nid}/rumors", headers=h).json()
    assert any(r["topic"] == "rival" for r in rumors) and any(
        r["topic"] == "grievance" for r in rumors
    )

    rel_out = client.post(
        f"/api/v1/establishments/{eid}/workers/{nid}/relieve", json={"reason": "Done"}, headers=h
    )
    assert rel_out.status_code == 200 and rel_out.json()["status"] == "relieved"


def test_found_settlement_and_upgrade_tier_flow(
    session_client: TestClient, spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
) -> None:
    """Found settlement, verify district slot caps per scale, and upgrade civic tier."""
    cid, mayor_id = str(uuid4()), "mayor_1"
    h = {"x-user-id": mayor_id}
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
    assert_stream_event(mock_bus, STREAM_WEST_MARCHES, "SettlementFounded")

    assert session_client.get(f"{url}/{sid}", headers=h).status_code == 200

    upg_url = f"/api/v1/settlements/{sid}/upgrade-tier"
    fail = session_client.post(upg_url, json={"new_tier": 2, "prosperity": 60}, headers=h)
    assert fail.status_code == 400 and "Insufficient civic prosperity" in fail.json()["detail"]

    upg = session_client.post(upg_url, json={"new_tier": 2, "prosperity": 150}, headers=h)
    assert upg.status_code == 200
    u = upg.json()
    assert u["tier"] == 2 and u["scale"] == "village" and u["max_districts"] == 4
    assert "defensive_palisade" in u["districts"]
    assert_stream_event(mock_bus, STREAM_WEST_MARCHES, "SettlementTierUpgraded")


def test_establishment_creation_and_worker_assignment(
    session_client: TestClient, spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
) -> None:
    """Place weaponsmith establishment, assign NPC armorer, and verify dynamic inventory."""
    cid, dm_id = str(uuid4()), f"dm_{uuid4().hex[:8]}"
    h = {"x-user-id": dm_id}
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
    assert_stream_event(mock_bus, STREAM_WEST_MARCHES, "EstablishmentConstructed")

    def _inv(i: str, s: int, p: int) -> dict:
        return {"item_id": i, "stock": s, "price_gp": p}

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
    assert_stream_event(mock_bus, STREAM_WEST_MARCHES, "NPCWorkerAssigned")

    roster = session_client.get(f"/api/v1/establishments/{eid}/workers", headers=h).json()
    assert len(roster) == 1
    shelf_items = [i["item_id"] for i in roster[0]["shelf_inventory"]]
    assert "blade_adamantine" in shelf_items and "plate_armor" in shelf_items
    assert len(roster[0]["backroom_inventory"]) == 1


def test_merchant_haggling_gambits_and_dm_override(
    session_client: TestClient, spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
) -> None:
    """Simulate persuasion rolls against merchant temperament and verify DM mood adjustment."""
    cid, dm_id, player_id = str(uuid4()), f"dm_{uuid4().hex[:8]}", f"p_{uuid4().hex[:8]}"
    asyncio.run(spicedb.write_relationship("campaign", cid, "dungeon_master", "user", dm_id))
    asyncio.run(spicedb.write_relationship("campaign", cid, "player", "user", player_id))
    dm_h, p_h = {"x-user-id": dm_id}, {"x-user-id": player_id}

    s_res = session_client.post(
        f"/api/v1/campaigns/{cid}/settlements",
        json={"name": "Oakhaven", "scale": "village", "districts": ["artisan"]},
        headers=dm_h,
    )
    sid = s_res.json()["settlement_id"]
    e_res = session_client.post(
        f"/api/v1/settlements/{sid}/establishments",
        json={"district_id": "artisan", "category": "commerce", "name": "Bram's Anvil"},
        headers=dm_h,
    )
    eid = e_res.json()["establishment_id"]

    h_data = {
        "character_id": "char_alys",
        "item_id": "blade",
        "item_name": "Blade",
        "base_price": 350,
    } | {
        "initial_offer_gp": 260,
        "gambit": "bulk_order_promise",
        "roll_value": 18,
        "campaign_id": cid,
        "temperament": "Stubborn",
    }
    haggle = session_client.post(
        f"/api/v1/establishments/{eid}/haggle", json=h_data, headers=p_h
    ).json()
    neg_id = haggle["negotiation_id"]
    assert haggle["status"] == "active" and haggle["counter_price"] < 350
    assert_stream_event(mock_bus, STREAM_TAVERN, "GambitExecuted")

    flatt = session_client.post(
        f"/api/v1/haggling/{neg_id}/gambit",
        json={"character_id": "char_alys", "gambit": "flattery", "roll_value": 16},
        headers=p_h,
    ).json()
    assert flatt["counter_price"] <= haggle["counter_price"]

    soothe = session_client.patch(
        f"/api/v1/haggling/{neg_id}/dm-override",
        json={"action": "soothe_merchant", "narrative_bark": "The blacksmith nods warmly."},
        headers=dm_h,
    )
    assert soothe.status_code == 200 and soothe.json()["merchant_mood_score"] > 0

    accept = session_client.patch(
        f"/api/v1/haggling/{neg_id}/dm-override",
        json={"action": "force_accept", "override_price_gp": 275, "narrative_bark": "Deal closed."},
        headers=dm_h,
    )
    assert (
        accept.status_code == 200
        and accept.json()["status"] == "completed"
        and accept.json()["counter_price"] == 275
    )
    assert_stream_event(mock_bus, STREAM_TAVERN, "NegotiationConcluded")
    assert_stream_event(mock_bus, STREAM_TAVERN, "CurrencyDeducted")


def test_bulletin_board_pin_and_cipher_decrypt(
    session_client: TestClient,
    gateway_client: TestClient,
    spicedb: MockSpiceDBClient,
    mock_bus: MockAsyncRedis,
) -> None:
    """Post bounty, decrypt hidden cipher notice, and verify WebSocket party broadcast."""
    cid, dm_id, player_id = str(uuid4()), f"dm_{uuid4().hex[:8]}", f"p_{uuid4().hex[:8]}"
    asyncio.run(spicedb.write_relationship("campaign", cid, "dungeon_master", "user", dm_id))
    asyncio.run(spicedb.write_relationship("campaign", cid, "player", "user", dm_id))
    asyncio.run(spicedb.write_relationship("campaign", cid, "player", "user", player_id))
    dm_h, p_h = {"x-user-id": dm_id}, {"x-user-id": player_id}

    s_res = session_client.post(
        f"/api/v1/campaigns/{cid}/settlements",
        json={"name": "Highspire Haven", "scale": "village"},
        headers=dm_h,
    )
    sid = s_res.json()["settlement_id"]
    base_url = f"/api/v1/settlements/{sid}/bulletin"

    b_data = {"board_type": "town_square", "title": "Wyvern", "category": "bounty"} | {
        "content": "300gp",
        "wax_sealed": True,
        "metadata": {"reward_gp": 300},
    }
    bounty = session_client.post(base_url, json=b_data, headers=dm_h)
    assert bounty.status_code == 201 and bounty.json()["wax_sealed"] is True
    assert_stream_event(mock_bus, STREAM_WEST_MARCHES, "BulletinNoticePinned")

    secret_text = "Midnight meeting behind the apothecary."
    c_data = {"board_type": "tavern", "title": "Meeting", "category": "rumor"} | {
        "content": "Note",
        "cipher_encoded": True,
        "cipher_solution": "gilded night",
        "hidden_content": secret_text,
    }
    nid = session_client.post(base_url, json=c_data, headers=dm_h).json()["notice_id"]

    notices = session_client.get(base_url, headers=p_h).json()
    assert any(
        n["notice_id"] == nid and not n["is_decrypted"] and not n["hidden_content"] for n in notices
    )

    dec = session_client.post(
        f"{base_url}/{nid}/decrypt", json={"solution": "gilded night"}, headers=p_h
    )
    assert dec.status_code == 200 and dec.json()["decrypted_content"] == secret_text
    assert_stream_event(mock_bus, STREAM_WEST_MARCHES, "CipherNoticeDecrypted")

    with (
        gateway_client.websocket_connect(f"/ws/campaigns/{cid}?user_id={dm_id}") as ws_dm,
        gateway_client.websocket_connect(f"/ws/campaigns/{cid}?user_id={player_id}") as ws_player,
    ):
        assert ws_dm.receive_json()["type"] == "connected"
        assert ws_player.receive_json()["type"] == "connected"
        ws_frame = {"action": "bulletin_bounty_posted", "settlement_id": sid, "notice_id": nid} | {
            "title": "Meeting",
            "is_decrypted": True,
        }
        ws_dm.send_json(ws_frame)
        assert ws_dm.receive_json()["action"] == "bulletin_bounty_posted"
        f_p = ws_player.receive_json()
        assert (
            f_p["action"] == "bulletin_bounty_posted"
            and f_p["notice_id"] == nid
            and f_p["is_decrypted"] is True
        )
