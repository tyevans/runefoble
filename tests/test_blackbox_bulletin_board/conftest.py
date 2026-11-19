"""Shared fixtures and assertion helpers for bulletin board blackbox tests.

Governed by ADR-0001, ADR-0002, ADR-0006, and Hard Invariant 7.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from game_session.main import app
from runefoble_auth.mock import MockSpiceDBClient

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.signing_test_issuer import SigningTestIssuer
from tests.helpers.ws_identity import SIGNING_ISSUER


@pytest.fixture
def client(
    spicedb: MockSpiceDBClient,
    mock_bus: MockAsyncRedis,
    trusted_ws_issuer: SigningTestIssuer,
) -> TestClient:
    return TestClient(app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"})
