"""Shared fixtures and harness for Campaign and Session Lobby blackbox tests.

Governed by ADR-0001, ADR-0003, ADR-0006, and Hard Invariants 6 and 7.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from character_sheet.dependencies import set_spicedb_client as set_char_spicedb
from character_sheet.main import app as character_app
from fastapi.testclient import TestClient
from game_session.dependencies import set_event_bus
from game_session.dependencies import set_spicedb_client as set_sess_spicedb
from game_session.main import app as session_app
from gateway_api.auth import get_spicedb_client
from gateway_api.main import app as gateway_app
from runefoble_platform.redis_bus import RedisStreamsEventBus

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import SIGNING_ISSUER


def auth_headers(sub: str) -> dict[str, str]:
    """Return Bearer headers for a token that the service verifier accepts."""
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


@pytest.fixture(autouse=True)
def reset_stores():
    """Configure isolated event bus and shared SpiceDB."""
    spicedb = get_spicedb_client()
    set_char_spicedb(spicedb)
    set_sess_spicedb(spicedb)
    mock_redis = MockAsyncRedis()
    bus = RedisStreamsEventBus(client=mock_redis)
    set_event_bus(bus)
    yield mock_redis
    set_event_bus(None)


@pytest.fixture
def client_gw(game_session_upstream, character_sheet_upstream) -> Iterator[TestClient]:
    with TestClient(gateway_app) as gateway_client:
        yield gateway_client


@pytest.fixture
def client_sess(game_session_upstream) -> Iterator[TestClient]:
    with TestClient(
        session_app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"}
    ) as session_client:
        yield session_client


@pytest.fixture
def client_char(game_session_upstream) -> Iterator[TestClient]:
    with TestClient(character_app, headers=auth_headers("character-owner")) as character_client:
        yield character_client
