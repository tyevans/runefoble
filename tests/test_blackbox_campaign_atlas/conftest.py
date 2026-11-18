"""Shared test fixtures for campaign atlas blackbox tests.

Governed by ADR-0001, ADR-0003, ADR-0007, and Hard Invariant 7.
"""

from collections.abc import Iterator
from uuid import uuid4

import pytest
from campaign_lore.dependencies import get_spicedb_client
from campaign_lore.identity import set_zitadel_auth_service
from campaign_lore.main import app
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import SpiceDBClient

from tests.helpers.ws_identity import SIGNING_ISSUER

VISITOR_SUBJECT = "lore-test-visitor"


def _bearer(user_id: str) -> dict[str, str]:
    """Return headers carrying a signed bearer token for `user_id`."""
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(user_id)}"}


@pytest.fixture(autouse=True)
def _trust_signing_issuer():
    """Campaign Lore verifies bearer tokens with the test issuer for each test in this module."""
    set_zitadel_auth_service(SIGNING_ISSUER.verifier())
    yield
    set_zitadel_auth_service(None)


@pytest.fixture
def client(lore_backends) -> Iterator[TestClient]:
    with TestClient(app, headers=_bearer(VISITOR_SUBJECT)) as client:
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
