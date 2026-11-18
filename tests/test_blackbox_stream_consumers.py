"""Blackbox tests for supervised Redis Streams consumers (TASK-0578).

Redis is an external process. Each test replaces only the Redis transport with MockAsyncRedis,
at the redis.asyncio.from_url boundary. Services start through their real FastAPI lifespans.
Events enter through the bus, and results are read through public HTTP routes or stream reads.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from typing import Any
from uuid import uuid4

import pytest
import redis.asyncio
from fastapi.testclient import TestClient
from runefoble_events.events import CombatEncounterStarted, SessionCreated
from runefoble_platform.consumer_group import RedisConsumerGroup
from runefoble_platform.redis_bus import RedisStreamsEventBus
from runefoble_platform.stream_consumer import StreamConsumer

from tests.helpers.campaign_analytics_service import AnalyticsService, wait_until
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import SIGNING_ISSUER

SESSION_STREAM = "runefoble.events.session"


def auth_headers(sub: str) -> dict[str, str]:
    """Return Bearer headers for a token that the service verifier accepts."""
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


@pytest.fixture
def redis_double(monkeypatch: pytest.MonkeyPatch) -> MockAsyncRedis:
    """Route every service-created Redis client to one in-memory transport double."""
    double = MockAsyncRedis()
    monkeypatch.setattr(redis.asyncio, "from_url", lambda *_args, **_kwargs: double)
    return double


def _wait_until(predicate: Callable[[], bool], timeout_s: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return predicate()


def _publish(double: MockAsyncRedis, stream: str, event: Any) -> None:
    asyncio.run(RedisStreamsEventBus(client=double).publish_event(stream, event))


def test_campaign_analytics_consumer_projects_session_event_from_redis(
    analytics_service: AnalyticsService,
) -> None:
    """A session event on Redis appears in the analytics timeline after the consumer starts."""
    campaign_id = f"camp-{uuid4().hex[:8]}"
    session_id = str(uuid4())
    analytics_service.grant_view(campaign_id)

    with analytics_service.start() as client:
        assert client.get("/healthz").json()["consumers"] == {"analytics": "running"}

        analytics_service.publish(
            SESSION_STREAM,
            SessionCreated(
                aggregate_id=session_id,
                session_id=session_id,
                campaign_id=campaign_id,
                title="Crypt of Shadows",
            ),
        )

        timeline_url = f"/api/v1/analytics/campaigns/{campaign_id}/timeline"

        def has_milestone() -> bool:
            body = client.get(timeline_url).json()
            return body.get("total_milestones", 0) >= 1

        assert wait_until(has_milestone), "analytics consumer did not project the session event"


def test_campaign_analytics_refuses_to_start_when_consumer_group_cannot_be_created(
    analytics_service: AnalyticsService, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A Redis failure at start-up stops the service. It does not run without its consumer."""
    from campaign_analytics.main import app

    class UnreachableRedis(MockAsyncRedis):
        async def xgroup_create(self, *_args: Any, **_kwargs: Any) -> bool:
            raise ConnectionError("redis unreachable")

    monkeypatch.setattr(redis.asyncio, "from_url", lambda *_a, **_k: UnreachableRedis())

    with pytest.raises(ConnectionError, match="redis unreachable"), TestClient(app):
        pass


def test_healthz_reports_failed_consumer_after_read_failure(
    analytics_service: AnalyticsService,
) -> None:
    """When the consumer loses Redis, /healthz reports it as failed with HTTP 503."""
    with analytics_service.start() as client:
        assert client.get("/healthz").status_code == 200

        async def lost_connection(*_args: Any, **_kwargs: Any) -> None:
            raise ConnectionError("redis connection lost")

        analytics_service.redis.xreadgroup = lost_connection  # type: ignore[method-assign]

        def is_degraded() -> bool:
            return client.get("/healthz").status_code == 503

        assert _wait_until(is_degraded)
        body = client.get("/healthz").json()
        assert body["status"] == "degraded"
        assert body["consumers"] == {"analytics": "failed"}


def test_soundscape_consumer_applies_combat_start_from_redis(
    redis_double: MockAsyncRedis, use_redis_client
) -> None:
    """A CombatEncounterStarted on the session stream raises encounter tension."""
    from soundscape.main import app
    from soundscape.scoring import calculate_encounter_tension

    session_id = str(uuid4())
    expected_tension = calculate_encounter_tension(
        combat_active=True, combat_round=1, enemy_cr_balance=2.0
    )
    use_redis_client(redis_double)

    with TestClient(app, headers=auth_headers("soundscape-tester")) as client:
        assert client.get("/healthz").json()["consumers"] == {"soundscape": "running"}
        tension_url = f"/api/v1/soundscape/tension?session_id={session_id}"
        assert client.get(tension_url).json()["tension_score"] != expected_tension

        _publish(
            redis_double,
            SESSION_STREAM,
            CombatEncounterStarted(
                aggregate_id=session_id,
                session_id=session_id,
                combatants=[{"combatant_id": "orc-1", "name": "Orc", "cr": 2.0}],
            ),
        )

        def tension_applied() -> bool:
            return client.get(tension_url).json()["tension_score"] == expected_tension

        assert _wait_until(tension_applied), "soundscape consumer did not apply the combat start"


def test_soundscape_consumer_settles_after_one_redis_delivery(
    redis_double: MockAsyncRedis, use_redis_client
) -> None:
    """One session event on Redis yields soundscape output once. The output count then stays fixed."""
    from soundscape.main import app

    session_id = str(uuid4())
    use_redis_client(redis_double)
    output_stream = "runefoble.events.soundscape"

    with TestClient(app, headers=auth_headers("soundscape-tester")) as client:
        _publish(
            redis_double,
            SESSION_STREAM,
            CombatEncounterStarted(
                aggregate_id=session_id,
                session_id=session_id,
                combatants=[{"combatant_id": "orc-1", "name": "Orc", "cr": 2.0}],
            ),
        )

        def output_written() -> bool:
            return len(redis_double.streams.get(output_stream, [])) > 0

        assert _wait_until(output_written), "soundscape consumer wrote no output"
        time.sleep(0.5)
        settled = len(redis_double.streams.get(output_stream, []))
        time.sleep(0.5)
        assert len(redis_double.streams.get(output_stream, [])) == settled
        assert client.get("/healthz").json()["consumers"] == {"soundscape": "running"}


@pytest.mark.asyncio
async def test_failed_handler_routes_message_to_dead_letter_and_acknowledges() -> None:
    """A handler failure dead-letters the message and acknowledges it. It is not left pending."""
    double = MockAsyncRedis()
    consumer_group = RedisConsumerGroup(client=double)

    async def failing_handler(_message_id: str, _event: Any) -> None:
        raise ValueError("projection write failed")

    consumer = StreamConsumer(
        consumer_group, SESSION_STREAM, "dlq_group", "dlq_worker", failing_handler
    )
    await consumer.ensure_group()
    await RedisStreamsEventBus(client=double).publish_event(
        SESSION_STREAM,
        SessionCreated(aggregate_id=uuid4(), session_id=str(uuid4()), campaign_id=str(uuid4())),
    )

    assert await consumer.poll_once() == 1

    assert consumer.dead_letter_count == 1
    assert consumer.processed_count == 0
    assert double.get_pending(SESSION_STREAM, "dlq_group") == {}
    dead_letters = double.streams[f"{SESSION_STREAM}.dlq"]
    assert len(dead_letters) == 1
    assert "projection write failed" in dead_letters[0][1]["error_reason"]
