"""Shared test fixtures for campaign atlas blackbox tests.

Governed by ADR-0001, ADR-0003, ADR-0007, and Hard Invariant 7.
"""

from collections.abc import Iterator
from uuid import uuid4

import pytest
from campaign_lore.main import app
from fastapi.testclient import TestClient

from tests.helpers.ws_identity import bearer

VISITOR_SUBJECT = "lore-test-visitor"


@pytest.fixture
def client(lore_backends) -> Iterator[TestClient]:
    with TestClient(app, headers=bearer(VISITOR_SUBJECT)) as client:
        yield client


@pytest.fixture
def campaign_id() -> str:
    return str(uuid4())


@pytest.fixture
def silverkeep_polygon() -> list[list[float]]:
    return [[100.0, 100.0], [300.0, 100.0], [300.0, 300.0], [100.0, 300.0]]
