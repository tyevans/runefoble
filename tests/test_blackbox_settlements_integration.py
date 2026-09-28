"""Blackbox integration tests for modular settlement auth, tokens, and permissions.

Governed by ADR-0001, ADR-0003, ADR-0005, ADR-0007, ADR-0013, and Hard Invariant 7.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated
from uuid import uuid4

import pytest
from fastapi import APIRouter, Depends, HTTPException
from fastapi.testclient import TestClient
from game_session.dependencies import set_event_bus, set_spicedb_client
from game_session.main import app
from game_session.settlement.auth import (
    AuthenticatedUser,
    decode_settlement_token,
    extract_bearer_token,
    get_current_settlement_user,
    require_establishment_manager,
    require_haven_builder,
    set_zitadel_auth_service,
)
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_auth.zitadel import ZitadelAuthService
from runefoble_platform.mock_redis import MockAsyncRedis
from runefoble_platform.redis_bus import RedisStreamsEventBus


@pytest.fixture
def mock_bus():
    bus_client = MockAsyncRedis()
    set_event_bus(RedisStreamsEventBus(client=bus_client))
    yield bus_client
    set_event_bus(None)


@pytest.fixture
def spicedb():
    db = MockSpiceDBClient()
    set_spicedb_client(db)
    yield db
    set_spicedb_client(None)


@pytest.fixture
def client(spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis) -> TestClient:
    return TestClient(app)


def test_auth_submodule_line_invariants():
    """Verify all extracted auth submodules remain strictly < 130 lines and auth.py < 40 lines."""
    base_dir = Path("services/game_session/src/game_session/settlement/auth")
    assert base_dir.is_dir(), "auth package directory must exist"

    auth_py = Path("services/game_session/src/game_session/settlement/auth.py")
    assert auth_py.exists(), "auth.py facade must exist"
    auth_lines = len(auth_py.read_text().splitlines())
    assert auth_lines < 40, f"auth.py must be strictly < 40 lines, got {auth_lines}"

    submodules = list(base_dir.glob("*.py"))
    assert len(submodules) >= 4, (
        "Expected at least tokens, permissions, relationships, dependencies"
    )

    for sm in submodules:
        lines = len(sm.read_text().splitlines())
        assert lines < 130, f"{sm.name} must be strictly < 130 lines per Invariant 6, got {lines}"


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

    # Dev mode decode fallback
    dev_user = decode_settlement_token(authorization=None, x_user_id="artisan_bob")
    assert dev_user.user_id == "artisan_bob"
    assert "player" in dev_user.roles

    # Production mode unauthorized without token
    service = ZitadelAuthService(dev_mode=False)
    set_zitadel_auth_service(service)
    try:
        with pytest.raises(HTTPException) as exc:
            decode_settlement_token(authorization=None, x_user_id="intruder")
        assert exc.value.status_code == 401
    finally:
        set_zitadel_auth_service(None)


@pytest.mark.asyncio
async def test_fastapi_route_dependencies(spicedb: MockSpiceDBClient):
    """Verify FastAPI dependency factories enforce Zanzibar object-level permissions."""
    test_router = APIRouter(prefix="/api/v1/test_auth")

    @test_router.get(
        "/havens/{settlement_id}/build",
        dependencies=[Depends(require_haven_builder("settlement_id"))],
    )
    async def build_endpoint(
        user: Annotated[AuthenticatedUser, Depends(get_current_settlement_user)],
    ):
        return {"status": "ok", "user": user.user_id}

    @test_router.get(
        "/establishments/{establishment_id}/manage",
        dependencies=[Depends(require_establishment_manager("establishment_id"))],
    )
    async def manage_endpoint(
        user: Annotated[AuthenticatedUser, Depends(get_current_settlement_user)],
    ):
        return {"status": "ok", "user": user.user_id}

    app.include_router(test_router)
    tc = TestClient(app)

    sid, eid = f"haven_{uuid4().hex[:6]}", f"est_{uuid4().hex[:6]}"
    builder, intruder = f"builder_{uuid4().hex[:6]}", f"intruder_{uuid4().hex[:6]}"

    await spicedb.write_relationship("settlement", sid, "upgrade", "user", builder)
    await spicedb.write_relationship("establishment", eid, "manage", "user", builder)

    # Builder succeeds
    res_build = tc.get(f"/api/v1/test_auth/havens/{sid}/build", headers={"x-user-id": builder})
    assert res_build.status_code == 200 and res_build.json()["user"] == builder

    res_est = tc.get(
        f"/api/v1/test_auth/establishments/{eid}/manage", headers={"x-user-id": builder}
    )
    assert res_est.status_code == 200 and res_est.json()["user"] == builder

    # Intruder rejected
    res_int_build = tc.get(f"/api/v1/test_auth/havens/{sid}/build", headers={"x-user-id": intruder})
    assert res_int_build.status_code == 403

    res_int_est = tc.get(
        f"/api/v1/test_auth/establishments/{eid}/manage", headers={"x-user-id": intruder}
    )
    assert res_int_est.status_code == 403


@pytest.mark.asyncio
async def test_frontdoor_settlement_auth_lifecycle(client: TestClient, spicedb: MockSpiceDBClient):
    """End-to-end blackbox frontdoor verifying authorization across settlement and establishment endpoints."""
    cid = str(uuid4())
    gm_id, player_id, intruder_id = (
        f"gm_{uuid4().hex[:6]}",
        f"p_{uuid4().hex[:6]}",
        f"int_{uuid4().hex[:6]}",
    )

    await spicedb.write_relationship("campaign", cid, "manage", "user", gm_id)
    await spicedb.write_relationship("campaign", cid, "play", "user", player_id)

    # Intruder cannot found settlement
    fail_res = client.post(
        f"/api/v1/campaigns/{cid}/settlements",
        json={"name": "Outlaw Camp", "scale": "hamlet"},
        headers={"x-user-id": intruder_id},
    )
    assert fail_res.status_code == 403

    # GM founds settlement
    found_res = client.post(
        f"/api/v1/campaigns/{cid}/settlements",
        json={"name": "Garrison Prime", "scale": "village"},
        headers={"x-user-id": gm_id},
    )
    assert found_res.status_code == 201
    sid = found_res.json()["settlement_id"]

    # Player can view settlement (discovering_campaign permission)
    view_res = client.get(
        f"/api/v1/campaigns/{cid}/settlements/{sid}", headers={"x-user-id": player_id}
    )
    assert view_res.status_code == 200

    # Intruder cannot view settlement
    intruder_view = client.get(
        f"/api/v1/campaigns/{cid}/settlements/{sid}", headers={"x-user-id": intruder_id}
    )
    assert intruder_view.status_code == 403


def test_workers_submodule_line_invariants():
    """Verify all extracted worker submodules remain strictly < 130 lines and workers_router.py < 40 lines."""
    base_dir = Path("services/game_session/src/game_session/settlement/workers")
    assert base_dir.is_dir(), "workers package directory must exist"

    router_py = Path("services/game_session/src/game_session/settlement/workers_router.py")
    assert router_py.exists(), "workers_router.py must exist"
    router_lines = len(router_py.read_text().splitlines())
    assert router_lines < 40, f"workers_router.py must be strictly < 40 lines, got {router_lines}"

    submodules = list(base_dir.glob("*.py"))
    assert len(submodules) >= 4, (
        "Expected at least loaders, operations, routes_roster, routes_relationships, routes_inventory"
    )

    for sm in submodules:
        lines = len(sm.read_text().splitlines())
        assert lines < 130, f"{sm.name} must be strictly < 130 lines per Invariant 6, got {lines}"


def test_workers_backwards_compatibility_exports():
    """Verify complete backwards compatibility of exported symbols from workers_router and workers."""
    import game_session.settlement.workers as workers_pkg
    import game_session.settlement.workers_router as wr_mod

    for sym in ["router", "roster_router", "relationships_router", "inventory_router"]:
        assert hasattr(wr_mod, sym), f"Missing exported symbol {sym} in workers_router"

    for sym in [
        "NPCWorkerAggregate",
        "AssignWorkerRequest",
        "NPCWorkerState",
        "RelieveWorkerRequest",
        "UpdateWorkerMoodRequest",
        "WorkerInventoryItem",
        "WorkerRelationship",
    ]:
        assert hasattr(workers_pkg, sym), f"Missing exported symbol {sym} in workers package"


@pytest.mark.asyncio
async def test_frontdoor_worker_modular_endpoints(
    client: TestClient, spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
):
    """Verify frontdoor execution across roster, relationships, rumors, and shelf inventory routers."""
    cid = str(uuid4())
    gm_id = f"gm_{uuid4().hex[:6]}"
    await spicedb.write_relationship("campaign", cid, "dungeon_master", "user", gm_id)
    await spicedb.write_relationship("campaign", cid, "player", "user", gm_id)
    h = {"x-user-id": gm_id}

    s_res = client.post(
        f"/api/v1/campaigns/{cid}/settlements",
        json={"name": "WorkerPort", "districts": ["market"]},
        headers=h,
    )
    sid = s_res.json()["settlement_id"]
    e_res = client.post(
        f"/api/v1/settlements/{sid}/establishments",
        json={"district_id": "market", "category": "commerce", "name": "Alchemy Haven"},
        headers=h,
    )
    eid = e_res.json()["establishment_id"]

    # 1. Assign worker with shelf & vault inventories and social ties
    assign_res = client.post(
        f"/api/v1/establishments/{eid}/workers",
        json={
            "name": "Alchemist Sarah",
            "role": "apothecary",
            "wage": 5,
            "shelf_inventory": [{"item_id": "healing_pot", "stock": 5, "price_gp": 25}],
            "vault_inventory": [
                {"item_id": "black_lotus", "stock": 1, "price_gp": 200, "is_contraband": True}
            ],
            "relationships": [
                {
                    "target_npc": "pip",
                    "relation": "rival",
                    "intensity": 0.6,
                    "notes": "Disputed recipe",
                }
            ],
            "metadata": {"grievance": "overdue_supply"},
        },
        headers=h,
    )
    assert assign_res.status_code == 201
    sarah = assign_res.json()
    nid = sarah["npc_id"]

    # 2. Worker detail lookup
    worker_detail = client.get(f"/api/v1/npcs/{nid}", headers=h).json()
    assert worker_detail["name"] == "Alchemist Sarah"

    # 3. Inventory routes: shelf stock, vault stock, item lookup, and restock
    inv_res = client.get(f"/api/v1/npcs/{nid}/inventory", headers=h).json()
    assert inv_res["total_shelf_items"] == 1
    assert inv_res["shelf_inventory"][0]["item_id"] == "healing_pot"

    vault_res = client.get(f"/api/v1/npcs/{nid}/inventory/vault", headers=h).json()
    assert len(vault_res) == 1 and vault_res[0]["item_id"] == "black_lotus"

    item_lookup = client.get(f"/api/v1/npcs/{nid}/inventory/healing_pot", headers=h).json()
    assert (item_lookup.get("price_gp") == 25 or item_lookup.get("unit_price") == 25) and (
        item_lookup.get("stock") == 5 or item_lookup.get("quantity") == 5
    )

    restock_res = client.post(
        f"/api/v1/npcs/{nid}/inventory/restock?destination=shelf",
        json={"item_id": "mana_potion", "quantity": 3, "unit_price": 40},
        headers=h,
    )
    assert restock_res.status_code == 200 and (
        restock_res.json().get("stock") == 3 or restock_res.json().get("quantity") == 3
    )

    # 4. Relationships and rumors routes
    rel_res = client.get(f"/api/v1/npcs/{nid}/relationships", headers=h).json()
    assert len(rel_res) == 1 and (
        rel_res[0].get("target_npc_id") == "pip" or rel_res[0].get("target_npc") == "pip"
    )

    rumor_res = client.get(f"/api/v1/npcs/{nid}/rumors", headers=h).json()
    assert any(r["topic"] == "rival" and "recipe" in r["detail"] for r in rumor_res)
    assert any(r["topic"] == "grievance" for r in rumor_res)

    # 5. Relieve worker
    rel_out = client.post(
        f"/api/v1/establishments/{eid}/workers/{nid}/relieve",
        json={"reason": "Contract completed"},
        headers=h,
    )
    assert rel_out.status_code == 200 and rel_out.json()["status"] == "relieved"
