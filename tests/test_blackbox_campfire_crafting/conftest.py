"""Shared test harness and fixtures for campfire crafting and downtime blackbox tests.

Governed by ADR-0003, ADR-0006, ADR-0007, ADR-0011, and Hard Invariant 7.
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from character_sheet.dependencies import set_event_bus as set_char_event_bus
from character_sheet.main import app as character_app
from fastapi.testclient import TestClient
from game_session.dependencies import set_event_bus as set_session_event_bus
from game_session.main import app as session_app
from gateway_api.auth import set_spicedb_client as set_gateway_spicedb
from gateway_api.main import app as gateway_app
from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient
from runefoble_auth.testing.signing_test_issuer import SigningTestIssuer
from runefoble_platform.redis_bus import RedisStreamsEventBus

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import SIGNING_ISSUER


def auth_headers(sub: str) -> dict[str, str]:
    """Return Bearer headers for a token that the service verifier accepts."""
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def mock_bus() -> Generator[MockAsyncRedis]:
    redis_client = MockAsyncRedis()
    bus = RedisStreamsEventBus(client=redis_client)
    set_char_event_bus(bus)
    set_session_event_bus(bus)
    yield redis_client
    set_char_event_bus(None)
    set_session_event_bus(None)


@pytest.fixture
def mock_spicedb() -> Generator[MockSpiceDBClient]:
    client = MockSpiceDBClient()
    set_gateway_spicedb(client)
    yield client
    set_gateway_spicedb(SpiceDBClient())


@pytest.fixture
def char_client() -> TestClient:
    return TestClient(character_app, headers=auth_headers("character-owner"))


@pytest.fixture
def session_client(trusted_ws_issuer: SigningTestIssuer) -> TestClient:
    return TestClient(
        session_app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"}
    )


@pytest.fixture
def gateway_client() -> TestClient:
    return TestClient(gateway_app)
