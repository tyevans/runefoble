"""Blackbox frontdoor tests: an approved audience weather modifier changes the session (TASK-0441).

Setup uses the public campaign and session routes. The modifier is published as the standard
`AudienceModifierApproved` event on `runefoble.events.audience`. The result is read through the
public session read. Redis is the only double (MockAsyncRedis). The consumer starts through the
real game_session lifespan. Governed by ADR-0006, ADR-0007, and ADR-0015.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Generator
from typing import Any
from uuid import uuid4

import pytest
import redis.asyncio
from fastapi.testclient import TestClient
from game_session.main import app as session_app
from runefoble_events.events import AudienceModifierApproved
from runefoble_platform.redis_bus import RedisStreamsEventBus

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.polling import wait_until
from tests.helpers.ws_identity import SIGNING_ISSUER

AUDIENCE_STREAM = "runefoble.events.audience"
AUDIENCE_DLQ = f"{AUDIENCE_STREAM}.dlq"
SESSION_STREAM = "runefoble.events.session"
WEATHER_EVENT = "runefoble.events.session.weather_changed"

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.fixture
def stream_redis(mock_bus, monkeypatch: pytest.MonkeyPatch) -> MockAsyncRedis:
    """One Redis double for the publisher and the game_session lifespan consumer."""
    monkeypatch.setattr(redis.asyncio, "from_url", lambda *_args, **_kwargs: mock_bus)
    return mock_bus


@pytest.fixture
def client(stream_redis: MockAsyncRedis) -> Generator[TestClient]:
    """Run the real lifespan, so the audience consumer starts and reads the stream."""
    headers = {"Authorization": f"Bearer {SIGNING_ISSUER.mint('dm-evelyn')}"}
    with TestClient(session_app, headers=headers) as test_client:
        assert test_client.get("/healthz").json()["consumers"] == {"game_session": "running"}
        yield test_client


def _create(client: TestClient) -> tuple[str, str]:
    """Create a campaign and a session in it through public routes. Return both ids."""
    campaign = client.post("/api/v1/campaigns", json={"title": "Tomb"})
    assert campaign.status_code == 201, campaign.text
    campaign_id = campaign.json()["id"]
    res = client.post(
        "/api/v1/sessions/create", json={"campaign_id": campaign_id, "title": "Crypt"}
    )
    assert res.status_code == 200, res.text
    return campaign_id, res.json()["session_id"]


def _approved(
    campaign_id: str,
    session_id: str,
    *,
    approved: bool = True,
    modifier_type: str = "weather_change",
    parameters: dict[str, Any] | None = None,
) -> AudienceModifierApproved:
    return AudienceModifierApproved(
        proposal_id=uuid4(),
        poll_id=uuid4(),
        campaign_id=campaign_id,
        session_id=session_id,
        approved_by="dm-evelyn",
        approved=approved,
        modifier_type=modifier_type,
        parameters=parameters if parameters is not None else {"weather": "dense fog"},
    )


def _publish(stream_redis: MockAsyncRedis, event: AudienceModifierApproved) -> None:
    async def _send() -> None:
        await RedisStreamsEventBus(client=stream_redis).publish_event(AUDIENCE_STREAM, event)

    asyncio.run(_send())


def _weather_events(stream_redis: MockAsyncRedis, session_id: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for _entry_id, fields in stream_redis.streams.get(SESSION_STREAM, []):
        payload = json.loads(fields["payload"])
        if fields["event_type"] == WEATHER_EVENT and str(payload.get("session_id")) == session_id:
            events.append(payload)
    return events


def _weather(client: TestClient, session_id: str) -> str | None:
    return client.get(f"/api/v1/sessions/{session_id}").json()["weather"]


def test_approved_weather_modifier_changes_the_session_weather(client, stream_redis) -> None:
    campaign_id, session_id = _create(client)
    _publish(stream_redis, _approved(campaign_id, session_id, parameters={"weather": "dense fog"}))

    assert wait_until(
        lambda: _weather(client, session_id) == "dense fog", timeout_s=10.0, interval_s=0.05
    )
    (event,) = _weather_events(stream_redis, session_id)
    assert event["weather"] == "dense fog"


def test_rejected_weather_modifier_changes_nothing(client, stream_redis) -> None:
    campaign_id, session_id = _create(client)
    _publish(
        stream_redis,
        _approved(campaign_id, session_id, approved=False, parameters={"weather": "storm"}),
    )
    # A later approved modifier is a barrier: the consumer reads the stream in order.
    _publish(stream_redis, _approved(campaign_id, session_id, parameters={"weather": "rain"}))

    assert wait_until(
        lambda: _weather(client, session_id) == "rain", timeout_s=10.0, interval_s=0.05
    )
    assert [event["weather"] for event in _weather_events(stream_redis, session_id)] == ["rain"]
    assert stream_redis.streams.get(AUDIENCE_DLQ, []) == []


def test_other_modifier_types_are_left_to_their_owners(client, stream_redis) -> None:
    campaign_id, session_id = _create(client)
    _publish(
        stream_redis,
        _approved(
            campaign_id,
            session_id,
            modifier_type="hazard_spawn",
            parameters={"hazard_type": "fire", "x": 2, "y": 3},
        ),
    )
    _publish(stream_redis, _approved(campaign_id, session_id, parameters={"weather": "rain"}))

    assert wait_until(
        lambda: _weather(client, session_id) == "rain", timeout_s=10.0, interval_s=0.05
    )
    assert [event["weather"] for event in _weather_events(stream_redis, session_id)] == ["rain"]
    assert stream_redis.streams.get(AUDIENCE_DLQ, []) == []


def test_weather_modifier_without_a_weather_value_is_dead_lettered(client, stream_redis) -> None:
    campaign_id, session_id = _create(client)
    _publish(stream_redis, _approved(campaign_id, session_id, parameters={}))

    assert wait_until(
        lambda: bool(stream_redis.streams.get(AUDIENCE_DLQ)), timeout_s=10.0, interval_s=0.05
    )
    (_entry_id, dead_letter), *_ = stream_redis.streams[AUDIENCE_DLQ]
    assert "weather" in dead_letter["error_reason"]
    assert _weather(client, session_id) is None
    assert _weather_events(stream_redis, session_id) == []
