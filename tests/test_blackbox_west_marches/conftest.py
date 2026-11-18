"""Shared fixtures and harness for West Marches blackbox test suite.

Governed by ADR-0001, ADR-0006, and Hard Invariant 7.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from game_session.dependencies import set_event_bus, set_spicedb_client
from game_session.main import app as session_app
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.redis_bus import RedisStreamsEventBus

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.fixture
def mock_bus() -> MockAsyncRedis:
    bus_client = MockAsyncRedis()
    set_event_bus(RedisStreamsEventBus(client=bus_client))
    yield bus_client
    set_event_bus(None)


@pytest.fixture
def spicedb_client() -> MockSpiceDBClient:
    db = MockSpiceDBClient()
    set_spicedb_client(db)
    yield db
    set_spicedb_client(None)


@pytest.fixture
def client(spicedb_client: MockSpiceDBClient) -> TestClient:
    return TestClient(
        session_app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"}
    )


def _auth(sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


@pytest.fixture
def party_ids(client: TestClient) -> dict[str, str]:
    """Create two party campaigns through public routes. The officer owns both (registration
    needs campaign ownership). Each player joins its own campaign through an invite."""
    officer, blue, gold = "rowan_officer", "blue_explorer", "gold_scout"
    ids = {"officer": officer, "blue_player": blue, "gold_player": gold}
    for key, player in (("campaign_blue", blue), ("campaign_gold", gold)):
        created = client.post("/api/v1/campaigns", json={"title": key}, headers=_auth(officer))
        assert created.status_code == 201, created.text
        cid = created.json()["id"]
        invite = client.post(
            f"/api/v1/campaigns/{cid}/invites", json={"role": "player"}, headers=_auth(officer)
        )
        assert invite.status_code == 201, invite.text
        joined = client.post(
            "/api/v1/campaigns/join",
            json={"invite_token": invite.json()["token"]},
            headers=_auth(player),
        )
        assert joined.status_code == 200, joined.text
        ids[key] = cid
    return ids
