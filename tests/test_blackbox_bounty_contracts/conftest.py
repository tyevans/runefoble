"""Shared fixtures and harness for mercenary bounty contracts blackbox tests.

Governed by ADR-0001, ADR-0006, ADR-0007, and Hard Invariant 7.
"""

from __future__ import annotations

from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session.dependencies import set_event_bus, set_spicedb_client
from game_session.events import STREAM_SESSION
from game_session.main import app as session_app
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.redis_bus import RedisStreamsEventBus

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.fixture
def mock_bus() -> Generator[MockAsyncRedis]:
    redis_client = MockAsyncRedis()
    bus = RedisStreamsEventBus(client=redis_client)
    set_event_bus(bus)
    yield redis_client
    set_event_bus(None)


@pytest.fixture
def spicedb() -> Generator[MockSpiceDBClient]:
    mock = MockSpiceDBClient()
    set_spicedb_client(mock)
    yield mock
    set_spicedb_client(None)


@pytest.fixture
def client(spicedb: MockSpiceDBClient) -> TestClient:
    return TestClient(
        session_app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"}
    )


def auth_headers(sub: str) -> dict[str, str]:
    """Return Bearer headers for a token that the game_session verifier accepts."""
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


def create_campaign_session(client: TestClient, owner_id: str) -> tuple[str, str]:
    """Create a campaign as its owner and return (campaign_id, first_session_id)."""
    res = client.post(
        "/api/v1/campaigns",
        json={"title": f"Bounty Campaign {uuid4().hex[:8]}"},
        headers=auth_headers(owner_id),
    )
    assert res.status_code == 201, res.text
    campaign_id = res.json()["id"]
    sessions = client.get(
        f"/api/v1/campaigns/{campaign_id}/sessions", headers=auth_headers(owner_id)
    )
    assert sessions.status_code == 200, sessions.text
    return campaign_id, sessions.json()[0]["id"]


def join_campaign(client: TestClient, campaign_id: str, owner_id: str, member_id: str) -> None:
    """Owner issues a player invite; the member redeems it through the public join route."""
    invite = client.post(
        f"/api/v1/campaigns/{campaign_id}/invites",
        json={"role": "player"},
        headers=auth_headers(owner_id),
    )
    assert invite.status_code == 201, invite.text
    joined = client.post(
        "/api/v1/campaigns/join",
        json={"invite_token": invite.json()["token"]},
        headers=auth_headers(member_id),
    )
    assert joined.status_code == 200, joined.text


def assert_session_stream_events(mock_bus: MockAsyncRedis, *event_names: str) -> None:
    """Verify published CloudEvents on the session Redis stream."""
    entries = mock_bus.streams.get(STREAM_SESSION, [])
    for event in event_names:
        assert any(event in str(entry[1]) for entry in entries), (
            f"Event '{event}' not found in {STREAM_SESSION}"
        )
