"""Shared fixtures and assertion helpers for settlement haven blackbox tests.

Governed by ADR-0001, ADR-0002, ADR-0007, ADR-0010, and Hard Invariant 7.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.mock import MockSpiceDBClient

from tests.helpers.game_session_app import session_app as app
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.fixture
def client(spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis) -> TestClient:
    return TestClient(app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"})
