"""Blackbox integration test suite for settlements, modular auth, establishments, workers, and haggling.

Part of TASK-0264 & TASK-0278 / PRD-0024 / US-0072, US-0073, US-0075, US-0076.
Governed by ADR-0001, ADR-0002, ADR-0005, ADR-0008, ADR-0010, and ADR-0013.
"""

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
from game_session.settlement.auth import (
    AuthenticatedUser,
    decode_settlement_token,
    extract_bearer_token,
    get_current_settlement_user,
    require_establishment_manager,
    require_haven_builder,
    set_zitadel_auth_service,
)
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
    assert any(ev_norm in str(e[1]).lower().replace("_", "") for e in entries), (
        f"Expected '{event_name}' in stream '{stream}', found: {entries}"
    )


# ---------------------------------------------------------------------------
# 1. Modular Auth & Permissions Blackbox Tests (TASK-0278)
# ---------------------------------------------------------------------------


def test_auth_submodule_line_invariants():
    """Verify all extracted auth submodules remain strictly < 130 lines and auth.py < 40 lines."""
    base_dir = Path("services/game_session/src/game_session/settlement/auth")
    auth_py = Path("services/game_session/src/game_session/settlement/auth.py")
    assert base_dir.is_dir() and auth_py.exists() and len(auth_py.read_text().splitlines()) < 40
    submodules = list(base_dir.glob("*.py"))
    assert len(submodules) >= 4, "Expected tokens, permissions, relationships, dependencies"
    for sm in submodules:
        lines = len(sm.read_text().splitlines())
        assert lines < 130, f"{sm.name} must be strictly < 130 lines, got {lines}"


def test_auth_backwards_compatibility_exports():
    """Verify complete backwards compatibility of exported symbols from game_session.settlement.auth."""
    import game_session.settlement.auth as auth_mod

    expected = [
        "check_campaign_write_permission",
        "check_settlement_read_permission",
        "check_settlement_write_permission",
        "check_establishment_read_permission",
        "check_establishment_write_permission",
        "check_establishment_play_permission",
        "check_npc_read_permission",
        "check_npc_write_permission",
        "check_negotiation_read_permission",
        "check_negotiation_participate_permission",
        "check_negotiation_arbitrate_permission",
        "write_settlement_relationships",
        "write_establishment_relationships",
        "write_npc_relationships",
        "write_negotiation_relationships",
        "get_current_settlement_user",
        "require_haven_builder",
        "require_establishment_manager",
        "extract_bearer_token",
        "decode_settlement_token",
        "AuthenticatedUser",
    ]
    for sym in expected:
        assert hasattr(auth_mod, sym), f"Missing exported symbol {sym} in auth facade"


def test_bearer_token_extraction_and_decoding():
    """Verify Zitadel bearer token extraction and dev mock resolution."""
    assert extract_bearer_token(None) is None
    assert extract_bearer_token("Basic 12345") is None
    assert extract_bearer_token("Bearer secret_jwt_token") == "secret_jwt_token"

    dev_user = decode_settlement_token(authorization=None, x_user_id="artisan_bob")
    assert dev_user.user_id == "artisan_bob" and "player" in dev_user.roles

    service = ZitadelAuthService(dev_mode=False)
    set_zitadel_auth_service(service)
    try:
        with pytest.raises(HTTPException) as exc:
            decode_settlement_token(authorization=None, x_user_id="intruder")
        assert exc.value.status_code == 401
    finally:
        set_zitadel_auth_service(None)


def test_fastapi_route_dependencies(spicedb: MockSpiceDBClient):
    """Verify FastAPI dependency factories enforce Zanzibar object-level permissions."""
    test_router = APIRouter(prefix="/api/v1/test_auth")

    @test_router.get("/h/{s}", dependencies=[Depends(require_haven_builder("s"))])
    async def h_ep(u: Annotated[AuthenticatedUser, Depends(get_current_settlement_user)]):
        return {"user": u.user_id}

    @test_router.get("/e/{e}", dependencies=[Depends(require_establishment_manager("e"))])
    async def e_ep(u: Annotated[AuthenticatedUser, Depends(get_current_settlement_user)]):
        return {"user": u.user_id}

    session_app.include_router(test_router)
    tc = TestClient(session_app)
    sid, eid = f"haven_{uuid4().hex[:6]}", f"est_{uuid4().hex[:6]}"
    builder, intruder = f"builder_{uuid4().hex[:6]}", f"intruder_{uuid4().hex[:6]}"

    asyncio.run(spicedb.write_relationship("settlement", sid, "upgrade", "user", builder))
    asyncio.run(spicedb.write_relationship("establishment", eid, "manage", "user", builder))

    res_build = tc.get(f"/api/v1/test_auth/h/{sid}", headers={"x-user-id": builder})
    assert res_build.status_code == 200 and res_build.json()["user"] == builder

    res_est = tc.get(f"/api/v1/test_auth/e/{eid}", headers={"x-user-id": builder})
    assert res_est.status_code == 200 and res_est.json()["user"] == builder

    assert tc.get(f"/api/v1/test_auth/h/{sid}", headers={"x-user-id": intruder}).status_code == 403
    assert tc.get(f"/api/v1/test_auth/e/{eid}", headers={"x-user-id": intruder}).status_code == 403


def test_frontdoor_settlement_auth_lifecycle(client: TestClient, spicedb: MockSpiceDBClient):
    """End-to-end blackbox frontdoor verifying authorization across settlement and establishment endpoints."""
    cid = str(uuid4())
    gm_id, player_id, intruder_id = (
        f"gm_{uuid4().hex[:6]}",
        f"p_{uuid4().hex[:6]}",
        f"int_{uuid4().hex[:6]}",
    )

    asyncio.run(spicedb.write_relationship("campaign", cid, "manage", "user", gm_id))
    asyncio.run(spicedb.write_relationship("campaign", cid, "play", "user", player_id))

    fail_res = client.post(
        f"/api/v1/campaigns/{cid}/settlements",
        json={"name": "Outlaw Camp", "scale": "hamlet"},
        headers={"x-user-id": intruder_id},
    )
    assert fail_res.status_code == 403

    found_res = client.post(
        f"/api/v1/campaigns/{cid}/settlements",
        json={"name": "Garrison Prime", "scale": "village"},
        headers={"x-user-id": gm_id},
    )
    assert found_res.status_code == 201
    sid = found_res.json()["settlement_id"]

    view_res = client.get(
        f"/api/v1/campaigns/{cid}/settlements/{sid}", headers={"x-user-id": player_id}
    )
    assert view_res.status_code == 200
    assert (
        client.get(
            f"/api/v1/campaigns/{cid}/settlements/{sid}", headers={"x-user-id": intruder_id}
        ).status_code
        == 403
    )


# ---------------------------------------------------------------------------
# 2. Settlement Lifecycle, Workers, Haggling, & Bulletin Tests (TASK-0264)
# ---------------------------------------------------------------------------


def test_found_settlement_and_upgrade_tier_flow(
    session_client: TestClient, spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
) -> None:
    """Found settlement, verify district slot caps per scale, and upgrade civic tier."""
    cid, mayor_id = str(uuid4()), f"mayor_{uuid4().hex[:8]}"
    h = {"x-user-id": mayor_id}
    asyncio.run(spicedb.write_relationship("campaign", cid, "dungeon_master", "user", mayor_id))
    asyncio.run(spicedb.write_relationship("campaign", cid, "player", "user", mayor_id))

    def _post(url: str, data: dict):
        return session_client.post(url, json=data, headers=h)

    # 1. Hamlet allows at most 2 districts: 3 districts must fail
    cap_res = _post(
        f"/api/v1/campaigns/{cid}/settlements",
        {"name": "TooBig", "scale": "hamlet", "districts": ["d1", "d2", "d3"]},
    )
    assert cap_res.status_code == 400 and "permits at most 2 districts" in cap_res.json()["detail"]

    # 2. Valid Hamlet founding with 2 districts succeeds
    found_res = _post(
        f"/api/v1/campaigns/{cid}/settlements",
        {"name": "Oak Crossing", "scale": "hamlet", "districts": ["commons", "residential"]},
    )
    assert found_res.status_code == 201
    sid = found_res.json()["settlement_id"]
    assert found_res.json()["scale"] == "hamlet" and found_res.json()["tier"] == 1
    assert_stream_event(mock_bus, STREAM_WEST_MARCHES, "SettlementFounded")

    # 3. Projection retrieval verifies persistent aggregate state
    proj = session_client.get(f"/api/v1/campaigns/{cid}/settlements/{sid}", headers=h)
    assert proj.status_code == 200 and proj.json()["settlement_id"] == sid

    # 4. Prosperity gate: Tier 2 requires 100 prosperity
    fail_upg = _post(f"/api/v1/settlements/{sid}/upgrade-tier", {"new_tier": 2, "prosperity": 60})
    assert (
        fail_upg.status_code == 400 and "Insufficient civic prosperity" in fail_upg.json()["detail"]
    )

    # 5. Successful upgrade to Village (tier 2) with expanded district cap (4)
    upg_res = _post(f"/api/v1/settlements/{sid}/upgrade-tier", {"new_tier": 2, "prosperity": 150})
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

    def _post(url: str, data: dict):
        return session_client.post(url, json=data, headers=h)

    sid = _post(
        f"/api/v1/campaigns/{cid}/settlements",
        {"name": "Ironhaven", "scale": "village", "districts": ["artisan_quarter"]},
    ).json()["settlement_id"]

    est_res = _post(
        f"/api/v1/settlements/{sid}/establishments",
        {"district_id": "artisan_quarter", "category": "commerce", "name": "The Ember Anvil"},
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
    worker_res = _post(f"/api/v1/establishments/{eid}/workers", worker_payload)
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

    def _dm_post(url: str, data: dict):
        return session_client.post(url, json=data, headers={"x-user-id": dm_id})

    sid = _dm_post(
        f"/api/v1/campaigns/{cid}/settlements",
        {"name": "Oakhaven", "scale": "village", "districts": ["artisan"]},
    ).json()["settlement_id"]
    eid = _dm_post(
        f"/api/v1/settlements/{sid}/establishments",
        {"district_id": "artisan", "category": "commerce", "name": "Bram's Anvil"},
    ).json()["establishment_id"]

    haggle_payload = {
        "character_id": "char_alys",
        "item_id": "folded_blade",
        "item_name": "Folded Blade",
        "base_price": 350,
        "initial_offer_gp": 260,
        "gambit": "bulk_order_promise",
        "roll_value": 18,
        "campaign_id": cid,
        "temperament": "Stubborn",
    }
    haggle = session_client.post(
        f"/api/v1/establishments/{eid}/haggle",
        json=haggle_payload,
        headers={"x-user-id": player_id},
    ).json()
    neg_id = haggle["negotiation_id"]
    assert haggle["status"] == "active" and haggle["counter_price"] < 350
    assert_stream_event(mock_bus, STREAM_TAVERN, "GambitExecuted")

    flatt = session_client.post(
        f"/api/v1/haggling/{neg_id}/gambit",
        json={"character_id": "char_alys", "gambit": "flattery", "roll_value": 16},
        headers={"x-user-id": player_id},
    ).json()
    assert flatt["counter_price"] <= haggle["counter_price"]

    def _dm_patch(data: dict):
        return session_client.patch(
            f"/api/v1/haggling/{neg_id}/dm-override", json=data, headers={"x-user-id": dm_id}
        )

    soothe = _dm_patch(
        {"action": "soothe_merchant", "narrative_bark": "The blacksmith nods warmly."}
    )
    assert soothe.status_code == 200 and soothe.json()["merchant_mood_score"] > 0

    accept = _dm_patch(
        {"action": "force_accept", "override_price_gp": 275, "narrative_bark": "Deal closed."}
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

    def _dm_post(url: str, data: dict):
        return session_client.post(url, json=data, headers={"x-user-id": dm_id})

    sid = _dm_post(
        f"/api/v1/campaigns/{cid}/settlements", {"name": "Highspire Haven", "scale": "village"}
    ).json()["settlement_id"]
    base_url = f"/api/v1/settlements/{sid}/bulletin"

    bounty_payload = {
        "board_type": "town_square",
        "title": "BOUNTY: Wyvern",
        "category": "bounty",
        "content": "300gp reward.",
        "wax_sealed": True,
        "metadata": {"reward_gp": 300},
    }
    bounty = _dm_post(base_url, bounty_payload)
    assert bounty.status_code == 201 and bounty.json()["wax_sealed"] is True
    assert_stream_event(mock_bus, STREAM_WEST_MARCHES, "BulletinNoticePinned")

    secret_text = "Midnight meeting behind the apothecary."
    cipher_payload = {
        "board_type": "tavern",
        "title": "Whispered Meeting",
        "category": "rumor",
        "content": "Secret note.",
        "cipher_encoded": True,
        "cipher_solution": "gilded night",
        "hidden_content": secret_text,
    }
    cipher = _dm_post(base_url, cipher_payload).json()
    nid = cipher["notice_id"]

    notices = session_client.get(base_url, headers={"x-user-id": player_id}).json()
    view = next(n for n in notices if n["notice_id"] == nid)
    assert view["is_decrypted"] is False and view["hidden_content"] is None

    dec = session_client.post(
        f"{base_url}/{nid}/decrypt",
        json={"solution": "gilded night"},
        headers={"x-user-id": player_id},
    )
    assert dec.status_code == 200 and dec.json()["decrypted_content"] == secret_text
    assert_stream_event(mock_bus, STREAM_WEST_MARCHES, "CipherNoticeDecrypted")

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
