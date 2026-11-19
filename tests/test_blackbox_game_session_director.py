"""Blackbox frontdoor tests: DM override and atmosphere routes on game_session (TASK-0581).

Setup uses the public create route. Actions and reads use public game_session HTTP routes.
Events are asserted on the published session stream. Governed by ADR-0011 and ADR-0015.
"""

from __future__ import annotations

import json
from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session.main import app as session_app

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import SIGNING_ISSUER

SESSION_STREAM = "runefoble.events.session"

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.fixture
def client() -> TestClient:
    return TestClient(
        session_app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('dm-evelyn')}"}
    )


@pytest.fixture
def stream_redis(mock_bus) -> Generator[MockAsyncRedis]:
    yield mock_bus


def _create(client: TestClient) -> str:
    """Create a campaign as its owner, then a session in it, through public routes."""
    campaign = client.post("/api/v1/campaigns", json={"title": "Tomb"})
    assert campaign.status_code == 201, campaign.text
    res = client.post(
        f"/api/v1/campaigns/{campaign.json()['id']}/sessions",
        json={"title": "Crypt"},
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


def test_create_is_refused_for_a_caller_without_run_session(client, stream_redis) -> None:
    """A stranger cannot create a session in a campaign. No session state is saved."""
    stranger = {"Authorization": f"Bearer {SIGNING_ISSUER.mint('stranger')}"}
    campaign = client.post("/api/v1/campaigns", json={"title": "Tomb"})
    # The campaign create seeds its first session, which publishes its own event.
    before = list(stream_redis.streams.get(SESSION_STREAM, []))
    res = client.post(
        f"/api/v1/campaigns/{campaign.json()['id']}/sessions",
        json={"title": "Uninvited"},
        headers=stranger,
    )
    assert res.status_code == 403, res.text
    assert stream_redis.streams.get(SESSION_STREAM, []) == before


def _published_types(mock_redis: MockAsyncRedis, session_id: str) -> list[str]:
    types: list[str] = []
    for _entry_id, fields in mock_redis.streams.get(SESSION_STREAM, []):
        payload = json.loads(fields["payload"])
        if str(payload.get("session_id")) == session_id:
            types.append(str(fields["event_type"]))
    return types


def test_dm_override_is_recorded_and_visible_in_the_next_read(client, stream_redis) -> None:
    session_id = _create(client)
    res = client.post(
        f"/api/v1/sessions/{session_id}/dm-override",
        json={"action": "reveal_trap", "reason": "DM veto", "payload": {"tile": "B4"}},
    )
    assert res.status_code == 200, res.text

    state = client.get(f"/api/v1/sessions/{session_id}").json()
    assert state["dm_overrides"] == [
        {"action": "reveal_trap", "reason": "DM veto", "payload": {"tile": "B4"}}
    ]
    assert "runefoble.events.session.dm_override_applied" in _published_types(
        stream_redis, session_id
    )


def test_atmosphere_update_is_visible_in_the_next_read(client, stream_redis) -> None:
    session_id = _create(client)
    res = client.post(
        f"/api/v1/sessions/{session_id}/atmosphere",
        json={"location_name": "Crypt", "lighting": "Dim", "mood": "Tense"},
    )
    assert res.status_code == 200, res.text

    state = client.get(f"/api/v1/sessions/{session_id}").json()
    assert state["atmosphere"]["location_name"] == "Crypt"
    assert state["atmosphere"]["lighting"] == "Dim"
    assert state["atmosphere"]["mood"] == "Tense"
    assert "runefoble.events.session.atmosphere_updated" in _published_types(
        stream_redis, session_id
    )


def test_atmosphere_defaults_are_applied_when_omitted(client) -> None:
    session_id = _create(client)
    client.post(f"/api/v1/sessions/{session_id}/atmosphere", json={"location_name": "Gate"})
    atmosphere = client.get(f"/api/v1/sessions/{session_id}").json()["atmosphere"]
    assert atmosphere["lighting"] == "Normal"
    assert atmosphere["mood"] == "Neutral"


def test_unknown_session_returns_404_for_both_routes(client) -> None:
    missing = uuid4()
    override = client.post(f"/api/v1/sessions/{missing}/dm-override", json={"action": "pause"})
    atmosphere = client.post(
        f"/api/v1/sessions/{missing}/atmosphere", json={"location_name": "Nowhere"}
    )
    assert override.status_code == 404
    assert atmosphere.status_code == 404
