"""Shared fixtures and harness for reaction interrupts and ready-action test suite."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.mock import MockSpiceDBClient

from tests.helpers.game_session_app import session_app
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.signing_test_issuer import SigningTestIssuer
from tests.helpers.the_watcher_app import watcher_app
from tests.helpers.ws_identity import SIGNING_ISSUER


@pytest.fixture
def client(
    mock_bus: MockAsyncRedis,
    spicedb: MockSpiceDBClient,
    trusted_ws_issuer: SigningTestIssuer,
) -> TestClient:
    return TestClient(
        session_app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"}
    )


@pytest.fixture
def watcher_client(mock_bus: MockAsyncRedis, trusted_ws_issuer: SigningTestIssuer) -> TestClient:
    return TestClient(
        watcher_app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"}
    )
