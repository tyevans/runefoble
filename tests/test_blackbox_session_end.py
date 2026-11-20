"""Blackbox frontdoor tests for `POST /api/v1/sessions/{session_id}/end` (TASK-0846 part a).

Setup uses public game_session routes. The DM holds `session.control`, so the DM ends the
session. A player holds `session.participate` only, so the player gets 403. Assertions read
the public session projection and the Redis Stream the owner publishes to.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from runefoble_platform.service_client import owner_routes

from tests.helpers.campaign_setup import add_member, create_campaign_session
from tests.helpers.game_session_app import session_app
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import bearer

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

SESSION_ENDED = "runefoble.events.session.ended"


@pytest.fixture
def session_client() -> TestClient:
    return TestClient(session_app)


def _published_types(mock_bus: MockAsyncRedis, session_id: str) -> list[str]:
    types: list[str] = []
    for entries in mock_bus.streams.values():
        for _entry_id, fields in entries:
            if fields.get("event_type") is None:
                continue
            payload = json.loads(fields["payload"])
            if str(payload.get("session_id")) == session_id:
                types.append(str(fields["event_type"]))
    return types


def _start(session_client: TestClient, session_id: str, owner_id: str) -> None:
    started = session_client.post(f"/api/v1/sessions/{session_id}/start", headers=bearer(owner_id))
    assert started.status_code == 200, started.text


def test_dm_ends_session_and_owner_publishes_session_ended(
    session_client: TestClient, mock_bus: MockAsyncRedis
) -> None:
    campaign_id, session_id = create_campaign_session(session_client, "dm_ender")
    _start(session_client, session_id, "dm_ender")

    route = owner_routes.end_session(session_id)
    res = session_client.request(route.method, route.path, headers=bearer("dm_ender"))

    assert res.status_code == 200, res.text
    assert res.json()["status"] == "ended"
    assert SESSION_ENDED in _published_types(mock_bus, session_id)


def test_player_cannot_end_session(session_client: TestClient, mock_bus: MockAsyncRedis) -> None:
    campaign_id, session_id = create_campaign_session(session_client, "dm_ender_player")
    add_member(campaign_id, "dm_ender_player", "player_ender", "player")

    res = session_client.post(f"/api/v1/sessions/{session_id}/end", headers=bearer("player_ender"))

    assert res.status_code == 403, res.text
    assert SESSION_ENDED not in _published_types(mock_bus, session_id)


def test_ending_a_lobby_session_is_refused(
    session_client: TestClient, mock_bus: MockAsyncRedis
) -> None:
    _campaign_id, session_id = create_campaign_session(session_client, "dm_ender_lobby")

    res = session_client.post(
        f"/api/v1/sessions/{session_id}/end", headers=bearer("dm_ender_lobby")
    )

    assert res.status_code == 400, res.text
    assert SESSION_ENDED not in _published_types(mock_bus, session_id)


def test_ending_an_ended_session_is_refused(session_client: TestClient) -> None:
    _campaign_id, session_id = create_campaign_session(session_client, "dm_ender_twice")
    _start(session_client, session_id, "dm_ender_twice")
    first = session_client.post(
        f"/api/v1/sessions/{session_id}/end", headers=bearer("dm_ender_twice")
    )
    assert first.status_code == 200, first.text

    second = session_client.post(
        f"/api/v1/sessions/{session_id}/end", headers=bearer("dm_ender_twice")
    )

    assert second.status_code == 400, second.text
