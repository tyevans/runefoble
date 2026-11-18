"""Shared test harness and fixtures for blackbox settlement tests.

Governed by ADR-0001, ADR-0006, and Hard Invariant 7 (Blackbox TDD).
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
def client(spicedb: MockSpiceDBClient) -> TestClient:
    return TestClient(app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"})


def assert_stream_events(mock_bus: MockAsyncRedis, *event_names: str) -> None:
    """Assert domain event was published to mock Redis stream."""
    entries = mock_bus.streams.get("runefoble.events.west_marches", [])
    for event in event_names:
        ev_norm = event.lower().replace("_", "")
        assert any(ev_norm in str(entry[1]).lower().replace("_", "") for entry in entries), (
            f"Expected event '{event}' in West Marches stream, but found: {entries}"
        )
