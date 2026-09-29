"""Shared fixtures and stream utilities for settlement blackbox integration tests."""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session.dependencies import set_event_bus as set_s_bus
from game_session.dependencies import set_spicedb_client as set_s_db
from game_session.main import app as session_app
from gateway_api.auth import set_spicedb_client as set_gw_db
from gateway_api.dependencies import set_event_bus as set_gw_bus
from gateway_api.main import app as gateway_app
from gateway_api.websocket_manager import ws_campaign_manager
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.mock_redis import MockAsyncRedis
from runefoble_platform.redis_bus import RedisStreamsEventBus


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
    db = MockSpiceDBClient()
    set_s_db(db)
    set_gw_db(db)
    yield db
    set_s_db(MockSpiceDBClient())
    set_gw_db(MockSpiceDBClient())


@pytest.fixture
def session_client(spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis) -> TestClient:
    return TestClient(session_app)


client = session_client


@pytest.fixture
def gateway_client(spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis) -> TestClient:
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


def _assert_submodules(dir_path: str, facade_path: str) -> None:
    base, facade = Path(dir_path), Path(facade_path)
    assert base.is_dir() and facade.exists() and len(facade.read_text().splitlines()) < 40
    submodules = list(base.glob("*.py"))
    assert len(submodules) >= 4 and all(len(s.read_text().splitlines()) < 130 for s in submodules)


def setup_campaign_settlement(
    tc: TestClient, db: MockSpiceDBClient, dist: list[str] | None = None
) -> tuple[str, str, str, dict[str, str], dict[str, str]]:
    cid, dm_id, p_id = str(uuid4()), f"dm_{uuid4().hex[:6]}", f"p_{uuid4().hex[:6]}"
    for r, u in [("player", p_id), ("player", dm_id), ("dungeon_master", dm_id)]:
        asyncio.run(db.write_relationship("campaign", cid, r, "user", u))
    h = {"x-user-id": dm_id}
    b = {"name": "Haven", "scale": "village", **({"districts": dist} if dist else {})}
    sid = tc.post(f"/api/v1/campaigns/{cid}/settlements", json=b, headers=h).json()["settlement_id"]
    return cid, sid, p_id, h, {"x-user-id": p_id}
