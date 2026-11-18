"""Shared fixtures and assertion helpers for settlement haven blackbox tests.

Governed by ADR-0001, ADR-0002, ADR-0007, ADR-0010, and Hard Invariant 7.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from game_session.main import app
from runefoble_auth.spicedb import MockSpiceDBClient

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.fixture
def client(spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis) -> TestClient:
    return TestClient(app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"})


def assert_event_emitted(mock_bus: MockAsyncRedis, event_name: str) -> None:
    """Verify that an event matching the given name was published to Redis streams."""
    entries = mock_bus.streams.get("runefoble.events.west_marches", [])
    ev_norm = event_name.lower().replace("_", "")
    assert any(ev_norm in str(entry[1]).lower().replace("_", "") for entry in entries), (
        f"Expected event '{event_name}' in stream, but found: {entries}"
    )
