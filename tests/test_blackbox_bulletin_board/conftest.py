"""Shared fixtures and assertion helpers for bulletin board blackbox tests.

Governed by ADR-0001, ADR-0002, ADR-0006, and Hard Invariant 7.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from game_session.events import STREAM_WEST_MARCHES
from game_session.main import app
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_auth.testing.signing_test_issuer import SigningTestIssuer

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import SIGNING_ISSUER


@pytest.fixture
def client(
    spicedb: MockSpiceDBClient,
    mock_bus: MockAsyncRedis,
    trusted_ws_issuer: SigningTestIssuer,
) -> TestClient:
    return TestClient(app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"})


def assert_event_emitted(mock_bus: MockAsyncRedis, event_name: str) -> None:
    """Verify that a domain event was published to the West Marches Redis stream."""
    entries = mock_bus.streams.get(STREAM_WEST_MARCHES, [])
    ev_norm = event_name.lower().replace("_", "")
    assert any(ev_norm in str(entry[1]).lower().replace("_", "") for entry in entries), (
        f"Expected event '{event_name}' in stream '{STREAM_WEST_MARCHES}', but found: {entries}"
    )
