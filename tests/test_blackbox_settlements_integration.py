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
