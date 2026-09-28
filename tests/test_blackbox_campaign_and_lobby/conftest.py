"""Shared fixtures and harness for Campaign and Session Lobby blackbox tests.

Governed by ADR-0001, ADR-0003, ADR-0006, and Hard Invariants 6 and 7.
"""

from __future__ import annotations

import pytest
from character_sheet.dependencies import set_spicedb_client as set_char_spicedb
from character_sheet.main import app as character_app
from fastapi.testclient import TestClient
from game_session.dependencies import set_event_bus
from game_session.dependencies import set_spicedb_client as set_sess_spicedb
from game_session.main import app as session_app
from gateway_api.auth import get_spicedb_client
from gateway_api.campaign_store import campaign_store
from gateway_api.main import app as gateway_app
from runefoble_platform.consumer_group import MockAsyncRedis
from runefoble_platform.redis_bus import RedisStreamsEventBus


@pytest.fixture(autouse=True)
def reset_stores():
    """Reset gateway campaign store and configure isolated event bus and shared SpiceDB."""
    campaign_store.reset()
    spicedb = get_spicedb_client()
    set_char_spicedb(spicedb)
    set_sess_spicedb(spicedb)
    mock_redis = MockAsyncRedis()
    bus = RedisStreamsEventBus(client=mock_redis)
    set_event_bus(bus)
    yield mock_redis
    set_event_bus(None)


@pytest.fixture
def client_gw() -> TestClient:
    return TestClient(gateway_app)


@pytest.fixture
def client_sess() -> TestClient:
    return TestClient(session_app)


@pytest.fixture
def client_char() -> TestClient:
    return TestClient(character_app)
