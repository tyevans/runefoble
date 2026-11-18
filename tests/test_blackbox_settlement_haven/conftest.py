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
