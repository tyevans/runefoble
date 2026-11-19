"""Shared fixtures and harness for caravan contracts blackbox tests.

Governed by: ADR-0001, ADR-0006, ADR-0011, Hard Invariant 7.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from game_session.main import app as session_app
from runefoble_auth.mock import MockSpiceDBClient

from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.fixture
def client(spicedb: MockSpiceDBClient) -> TestClient:
    return TestClient(
        session_app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"}
    )
