"""Shared test fixtures for campaign atlas blackbox tests.

Governed by ADR-0001, ADR-0003, ADR-0007, and Hard Invariant 7.
"""

from collections.abc import Iterator
from uuid import uuid4

import pytest
from campaign_lore.dependencies import get_spicedb_client
from campaign_lore.main import app
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import SpiceDBClient


@pytest.fixture
def client(lore_backends) -> Iterator[TestClient]:
    with TestClient(app) as client:
        yield client


@pytest.fixture
def spicedb() -> SpiceDBClient:
    return get_spicedb_client()


@pytest.fixture
def campaign_id() -> str:
    return str(uuid4())


@pytest.fixture
def silverkeep_polygon() -> list[list[float]]:
    return [[100.0, 100.0], [300.0, 100.0], [300.0, 300.0], [100.0, 300.0]]
