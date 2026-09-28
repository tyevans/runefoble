"""Blackbox integration test suite for settlement havens, establishments, workers, haggling, and bulletin boards.

Part of TASK-0264 / PRD-0024 / US-0072, US-0073, US-0075, US-0076.
Governed by ADR-0001 (SpiceDB Zanzibar), ADR-0002 (Domain Events via eventsource-py),
ADR-0008 (Blackbox Testing), and ADR-0010 (CI Pipeline).
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
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
from gateway_api.auth import set_spicedb_client as set_gateway_spicedb
from gateway_api.dependencies import set_event_bus as set_gateway_bus
from gateway_api.main import app as gateway_app
from runefoble_auth.spicedb import MockSpiceDBClient
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
    assert any(ev_norm in str(entry[1]).lower().replace("_", "") for entry in entries), (
        f"Expected event '{event_name}' in stream '{stream}', but found: {entries}"
    )


def test_found_settlement_and_upgrade_tier_flow(
    session_client: TestClient, spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
) -> None:
    """Found settlement, verify district slot caps per scale, and upgrade civic tier."""
    cid, mayor_id = str(uuid4()), f"mayor_{uuid4().hex[:8]}"
    h = {"x-user-id": mayor_id}
    asyncio.run(spicedb.write_relationship("campaign", cid, "dungeon_master", "user", mayor_id))
    asyncio.run(spicedb.write_relationship("campaign", cid, "player", "user", mayor_id))

    # 1. Hamlet allows at most 2 districts: 3 districts must fail
    cap_res = session_client.post(
        f"/api/v1/campaigns/{cid}/settlements",
        json={"name": "TooBig", "scale": "hamlet", "districts": ["d1", "d2", "d3"]},
        headers=h,
    )
    assert cap_res.status_code == 400 and "permits at most 2 districts" in cap_res.json()["detail"]

    # 2. Valid Hamlet founding with 2 districts succeeds
    found_res = session_client.post(
        f"/api/v1/campaigns/{cid}/settlements",
        json={"name": "Oak Crossing", "scale": "hamlet", "districts": ["commons", "residential"]},
        headers=h,
    )
    assert found_res.status_code == 201
    sid = found_res.json()["settlement_id"]
    assert found_res.json()["scale"] == "hamlet" and found_res.json()["tier"] == 1
    assert_stream_event(mock_bus, STREAM_WEST_MARCHES, "SettlementFounded")

    # 3. Projection retrieval verifies persistent aggregate state
    proj = session_client.get(f"/api/v1/campaigns/{cid}/settlements/{sid}", headers=h)
    assert proj.status_code == 200 and proj.json()["settlement_id"] == sid

    # 4. Prosperity gate: Tier 2 requires 100 prosperity
    fail_upg = session_client.post(
        f"/api/v1/settlements/{sid}/upgrade-tier", json={"new_tier": 2, "prosperity": 60}, headers=h
    )
    assert (
        fail_upg.status_code == 400 and "Insufficient civic prosperity" in fail_upg.json()["detail"]
    )

    # 5. Successful upgrade to Village (tier 2) with expanded district cap (4)
    upg_res = session_client.post(
        f"/api/v1/settlements/{sid}/upgrade-tier",
        json={"new_tier": 2, "prosperity": 150},
        headers=h,
    )
    assert upg_res.status_code == 200
    upgraded = upg_res.json()
    assert (
        upgraded["tier"] == 2 and upgraded["scale"] == "village" and upgraded["max_districts"] == 4
    )
    assert "defensive_palisade" in upgraded["districts"]
    assert_stream_event(mock_bus, STREAM_WEST_MARCHES, "SettlementTierUpgraded")


def test_establishment_creation_and_worker_assignment(
    session_client: TestClient, spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
) -> None:
    """Place weaponsmith establishment, assign NPC armorer, and verify dynamic inventory."""
    cid, dm_id = str(uuid4()), f"dm_{uuid4().hex[:8]}"
    h = {"x-user-id": dm_id}
    asyncio.run(spicedb.write_relationship("campaign", cid, "dungeon_master", "user", dm_id))
    asyncio.run(spicedb.write_relationship("campaign", cid, "player", "user", dm_id))

    # 1. Found settlement & place weaponsmith commerce establishment
    sid = session_client.post(
        f"/api/v1/campaigns/{cid}/settlements",
        json={"name": "Ironhaven", "scale": "village", "districts": ["artisan_quarter"]},
        headers=h,
    ).json()["settlement_id"]

    est_res = session_client.post(
        f"/api/v1/settlements/{sid}/establishments",
        json={"district_id": "artisan_quarter", "category": "commerce", "name": "The Ember Anvil"},
        headers=h,
    )
    assert est_res.status_code == 201
    eid = est_res.json()["establishment_id"]
    assert_stream_event(mock_bus, STREAM_WEST_MARCHES, "EstablishmentConstructed")

    # 2. Assign NPC armorer with custom shelf and vault inventory
    worker_res = session_client.post(
        f"/api/v1/establishments/{eid}/workers",
        json={
            "name": "Korgan Deepforge",
            "role": "armorer",
            "wage": 10,
            "trade_proficiencies": ["blacksmithing", "armorer"],
            "shelf_inventory": [
                {"item_id": "blade_adamantine", "stock": 3, "price_gp": 350},
                {"item_id": "plate_armor", "stock": 1, "price_gp": 1500},
            ],
            "vault_inventory": [{"item_id": "iron_ingots", "stock": 40, "price_gp": 5}],
            "temperament": "Stubborn",
            "patience": 5,
        },
        headers=h,
    )
    assert worker_res.status_code == 201
    worker = worker_res.json()
    assert worker["role"] == "armorer" and worker["service_quality_contribution"] > 1.2
    assert_stream_event(mock_bus, STREAM_WEST_MARCHES, "NPCWorkerAssigned")

    # 3. Verify dynamic inventory visible on public workers frontdoor
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

    sid = session_client.post(
        f"/api/v1/campaigns/{cid}/settlements",
        json={"name": "Oakhaven", "scale": "village", "districts": ["artisan"]},
        headers={"x-user-id": dm_id},
    ).json()["settlement_id"]
    eid = session_client.post(
        f"/api/v1/settlements/{sid}/establishments",
        json={"district_id": "artisan", "category": "commerce", "name": "Bram's Anvil"},
        headers={"x-user-id": dm_id},
    ).json()["establishment_id"]

    # 1. Player initiates haggling for 350gp blade with Bulk Order Promise
    haggle = session_client.post(
        f"/api/v1/establishments/{eid}/haggle",
        json={
            "character_id": "char_alys",
            "item_id": "folded_blade",
            "item_name": "Folded Blade",
            "base_price": 350,
            "initial_offer_gp": 260,
            "gambit": "bulk_order_promise",
            "roll_value": 18,
            "campaign_id": cid,
            "temperament": "Stubborn",
        },
        headers={"x-user-id": player_id},
    ).json()
    neg_id = haggle["negotiation_id"]
    assert haggle["status"] == "active" and haggle["counter_price"] < 350
    assert_stream_event(mock_bus, STREAM_TAVERN, "GambitExecuted")

    # 2. Flattery gambit further reduces price
    flatt = session_client.post(
        f"/api/v1/haggling/{neg_id}/gambit",
        json={"character_id": "char_alys", "gambit": "flattery", "roll_value": 16},
        headers={"x-user-id": player_id},
    ).json()
    assert flatt["counter_price"] <= haggle["counter_price"]

    # 3. DM adjusts merchant mood
    soothe = session_client.patch(
        f"/api/v1/haggling/{neg_id}/dm-override",
        json={"action": "soothe_merchant", "narrative_bark": "The blacksmith nods warmly."},
        headers={"x-user-id": dm_id},
    )
    assert soothe.status_code == 200 and soothe.json()["merchant_mood_score"] > 0

    # 4. DM executes force accept arbitration
    accept = session_client.patch(
        f"/api/v1/haggling/{neg_id}/dm-override",
        json={"action": "force_accept", "override_price_gp": 275, "narrative_bark": "Deal closed."},
        headers={"x-user-id": dm_id},
    )
    assert accept.status_code == 200 and accept.json()["status"] == "completed"
    assert accept.json()["counter_price"] == 275
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

    sid = session_client.post(
        f"/api/v1/campaigns/{cid}/settlements",
        json={"name": "Highspire Haven", "scale": "village"},
        headers={"x-user-id": dm_id},
    ).json()["settlement_id"]
    base_url = f"/api/v1/settlements/{sid}/bulletin"

    # 1. Post monster bounty with wax seal
    bounty = session_client.post(
        base_url,
        json={
            "board_type": "town_square",
            "title": "BOUNTY: Wyvern",
            "category": "bounty",
            "content": "300gp reward.",
            "wax_sealed": True,
            "metadata": {"reward_gp": 300},
        },
        headers={"x-user-id": dm_id},
    )
    assert bounty.status_code == 201 and bounty.json()["wax_sealed"] is True
    assert_stream_event(mock_bus, STREAM_WEST_MARCHES, "BulletinNoticePinned")

    # 2. Post secret cipher notice & verify masking before decryption
    secret_text = "Midnight meeting behind the apothecary."
    cipher = session_client.post(
        base_url,
        json={
            "board_type": "tavern",
            "title": "Whispered Meeting",
            "category": "rumor",
            "content": "Secret note.",
            "cipher_encoded": True,
            "cipher_solution": "gilded night",
            "hidden_content": secret_text,
        },
        headers={"x-user-id": dm_id},
    ).json()
    nid = cipher["notice_id"]

    notices = session_client.get(base_url, headers={"x-user-id": player_id}).json()
    view = next(n for n in notices if n["notice_id"] == nid)
    assert view["is_decrypted"] is False and view["hidden_content"] is None

    # 3. Decrypt cipher notice
    dec = session_client.post(
        f"{base_url}/{nid}/decrypt",
        json={"solution": "gilded night"},
        headers={"x-user-id": player_id},
    )
    assert dec.status_code == 200 and dec.json()["decrypted_content"] == secret_text
    assert_stream_event(mock_bus, STREAM_WEST_MARCHES, "CipherNoticeDecrypted")

    # 4. Verify real-time party WebSocket broadcast
    with gateway_client.websocket_connect(f"/ws/campaigns/{cid}?user_id={dm_id}") as ws_dm:
        assert ws_dm.receive_json()["type"] == "connected"
        with gateway_client.websocket_connect(
            f"/ws/campaigns/{cid}?user_id={player_id}"
        ) as ws_player:
            assert ws_player.receive_json()["type"] == "connected"
            ws_dm.send_json(
                {
                    "action": "bulletin_bounty_posted",
                    "settlement_id": sid,
                    "notice_id": nid,
                    "title": "Whispered Meeting",
                    "is_decrypted": True,
                }
            )
            frame_dm = ws_dm.receive_json()
            frame_player = ws_player.receive_json()
            assert frame_dm["action"] == "bulletin_bounty_posted"
            assert frame_player["action"] == "bulletin_bounty_posted"
            assert frame_player["notice_id"] == nid and frame_player["is_decrypted"] is True
