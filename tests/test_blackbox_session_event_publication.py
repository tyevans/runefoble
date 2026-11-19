"""Blackbox frontdoor tests for TASK-0565: session events persisted through aggregates and published.

Governed by:
- ADR-0011: state transitions are events saved through AggregateRepository
- ADR-0006: Redis Streams event streaming
- Hard Invariant 7: blackbox TDD with frontdoor setup

Setup and actions use only public game_session HTTP routes. Assertions read the
published Redis Stream runefoble.events.session and the public session projection.
"""

from __future__ import annotations

import json
from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session.main import app as session_app

from tests.helpers.campaign_setup import create_campaign
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import SIGNING_ISSUER

SESSION_STREAM = "runefoble.events.session"


pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.fixture
def session_client() -> TestClient:
    return TestClient(
        session_app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"}
    )


@pytest.fixture
def stream_redis(mock_bus) -> Generator[MockAsyncRedis]:
    yield mock_bus


def _published_event_types(mock_redis: MockAsyncRedis, session_id: str) -> list[str]:
    """Return the event types published to the session stream for one session."""
    entries = mock_redis.streams.get(SESSION_STREAM, [])
    types: list[str] = []
    for _entry_id, fields in entries:
        payload = json.loads(fields["payload"])
        if (
            str(payload.get("session_id")) == session_id
            or str(payload.get("aggregate_id")) == session_id
        ):
            types.append(str(fields["event_type"]))
    return types


def _create_joined_session(client: TestClient) -> str:
    campaign_id = create_campaign(client, "test-user")
    created = client.post(
        f"/api/v1/campaigns/{campaign_id}/sessions",
        json={"title": "Publication Session"},
    )
    assert created.status_code == 201, created.text
    session_id = created.json()["id"]
    joined = client.post(
        f"/api/v1/sessions/{session_id}/join",
        json={
            "character_id": str(uuid4()),
            "character_name": "Valeros",
            "character_class": "Fighter",
        },
    )
    assert joined.status_code == 200, joined.text
    return session_id


def test_next_turn_publishes_turn_advanced_once_to_session_stream(
    session_client: TestClient, stream_redis: MockAsyncRedis
) -> None:
    """Advancing the turn through the public route publishes one TurnAdvanced event."""
    session_id = _create_joined_session(session_client)
    assert session_client.post(f"/api/v1/sessions/{session_id}/start").status_code == 200

    res = session_client.post(f"/api/v1/sessions/{session_id}/next-turn")

    assert res.status_code == 200, res.text
    types = _published_event_types(stream_redis, session_id)
    assert types.count("runefoble.events.session.turn_advanced") == 1


def test_dice_roll_for_unknown_session_returns_not_found(
    session_client: TestClient, stream_redis: MockAsyncRedis
) -> None:
    """A roll for a session that does not exist is refused and publishes nothing.

    The permission check runs first, so an unknown session reads as forbidden.
    """
    unknown = uuid4()

    res = session_client.post(f"/api/v1/sessions/{unknown}/roll", json={"formula": "1d20"})

    assert res.status_code == 403
    assert _published_event_types(stream_redis, str(unknown)) == []


def test_lobby_readiness_toggle_is_returned_by_session_state(
    session_client: TestClient, stream_redis: MockAsyncRedis
) -> None:
    """Toggling readiness through the lobby route stores it in the session state."""
    session_id = _create_joined_session(session_client)

    res = session_client.post(
        f"/api/v1/sessions/{session_id}/lobby/readiness",
        json={"is_ready": True},
    )
    assert res.status_code == 200, res.text

    state = session_client.get(f"/api/v1/sessions/{session_id}")
    assert state.status_code == 200
    assert state.json()["lobby_readiness"] == {"test-user": True}
    types = _published_event_types(stream_redis, session_id)
    assert types.count("runefoble.events.session.readiness_toggled") == 1
