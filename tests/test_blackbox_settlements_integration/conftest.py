"""Shared fixtures and stream utilities for settlement blackbox integration tests."""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session.dependencies import set_event_bus as set_s_bus
from game_session.dependencies import set_spicedb_client as set_s_db
from game_session.main import app as session_app
from game_session.settlement import auth as settlement_auth
from gateway_api.auth import set_zitadel_auth_service as set_gw_verifier
from gateway_api.dependencies import set_event_bus as set_gw_bus
from gateway_api.main import app as gateway_app
from gateway_api.websocket_manager import ws_campaign_manager
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_auth.testing.signing_test_issuer import SigningTestIssuer
from runefoble_platform.redis_bus import RedisStreamsEventBus

from tests.helpers.mock_redis import MockAsyncRedis


@pytest.fixture
def mock_bus() -> Generator[MockAsyncRedis]:
    client = MockAsyncRedis()
    bus = RedisStreamsEventBus(client=client)
    set_s_bus(bus)
    set_gw_bus(bus)
    yield client
    set_s_bus(None)
    set_gw_bus(None)


@pytest.fixture
def spicedb() -> Generator[MockSpiceDBClient]:
    db = get_spicedb_client()
    set_s_db(db)
    yield db
    set_s_db(MockSpiceDBClient())


@pytest.fixture
def settlement_issuer() -> Generator[SigningTestIssuer]:
    """Trust one signing issuer in the game_session and gateway verifiers for one test."""
    issuer = SigningTestIssuer()
    verifier = issuer.verifier()
    settlement_auth.set_zitadel_auth_service(verifier)
    set_gw_verifier(verifier)
    yield issuer
    settlement_auth.set_zitadel_auth_service(None)
    set_gw_verifier(None)


def bearer_headers(issuer: SigningTestIssuer, sub: str) -> dict[str, str]:
    """Return Authorization headers carrying a token that the verifiers accept for `sub`."""
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


def ws_subprotocols(headers: dict[str, str]) -> list[str]:
    """Return the WebSocket subprotocols that carry the bearer token from `headers`."""
    token = headers["Authorization"].removeprefix("Bearer ")
    return ["runefoble.v1", f"runefoble.bearer.{token}"]


@pytest.fixture
def session_client(spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis) -> TestClient:
    return TestClient(session_app)


client = session_client


@pytest.fixture
def gateway_client(
    spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis, settlement_issuer: SigningTestIssuer
) -> TestClient:
    return TestClient(gateway_app)


@pytest.fixture(autouse=True)
def clean_gateway_ws() -> Generator[None]:
    ws_campaign_manager.active_connections.clear()
    yield
    ws_campaign_manager.active_connections.clear()


def assert_stream_event(mock_bus: MockAsyncRedis, stream: str, event_name: str) -> None:
    ev_norm = event_name.lower().replace("_", "")
    assert any(
        ev_norm in str(e[1]).lower().replace("_", "") for e in mock_bus.streams.get(stream, [])
    )


def setup_campaign_settlement(
    tc: TestClient,
    db: MockSpiceDBClient,
    dist: list[str] | None = None,
    issuer: SigningTestIssuer | None = None,
) -> tuple[str, str, str, dict[str, str], dict[str, str]]:
    """Create a campaign and a haven. Pass `issuer` to send signed bearer tokens instead."""
    cid, dm_id, p_id = str(uuid4()), f"dm_{uuid4().hex[:6]}", f"p_{uuid4().hex[:6]}"
    for r, u in [("player", p_id), ("player", dm_id), ("dungeon_master", dm_id)]:
        asyncio.run(db.write_relationship("campaign", cid, r, "user", u))
    if issuer is None:
        h, p_h = {"x-user-id": dm_id}, {"x-user-id": p_id}
    else:
        h, p_h = bearer_headers(issuer, dm_id), bearer_headers(issuer, p_id)
    b = {"name": "Haven", "scale": "village", **({"districts": dist} if dist else {})}
    sid = tc.post(f"/api/v1/campaigns/{cid}/settlements", json=b, headers=h).json()["settlement_id"]
    return cid, sid, p_id, h, p_h
