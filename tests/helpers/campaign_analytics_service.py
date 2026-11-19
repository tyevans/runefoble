"""Start the Campaign Analytics service on a real PostgreSQL container and a Redis double.

PostgreSQL is the container from the `postgres_service` fixture. Redis is an external process,
so the double replaces only the redis.asyncio client at the connection boundary. The service
starts through its real lifespan. Each `start()` call is a new process-equivalent start, so a
second start after the first one exits is a restart.

Governed by ADR-0011, ADR-0015, and Hard Invariant 7 (events in and HTTP reads out).
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import pytest
import redis.asyncio
from campaign_analytics.main import create_app_from_environment
from fastapi.testclient import TestClient
from runefoble_auth.mock import MockSpiceDBClient
from runefoble_platform.event_sourcing import get_event_store, set_event_store
from runefoble_platform.redis_bus import RedisStreamsEventBus

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.module_state import restored_seam
from tests.helpers.spicedb_factory import shared_spicedb_client
from tests.helpers.ws_identity import bearer

SESSION_STREAM = "runefoble.events.session"
BOARD_STREAM = "runefoble.events.board"
CHARACTER_STREAM = "runefoble.events.character"
WATCHER_STREAM = "runefoble.events.watcher"

SERVICE_SUBJECT = "user-test"


@dataclass
class AnalyticsService:
    """One PostgreSQL database and one Redis transport shared by every start of the service."""

    dsn: str
    redis: MockAsyncRedis
    spicedb: MockSpiceDBClient

    def publish(self, stream: str, event: Any) -> None:
        """Publish a domain event to a stream, as a producing service does."""
        asyncio.run(RedisStreamsEventBus(client=self.redis).publish_event(stream, event))

    def redeliver(self, stream: str, group: str = "campaign_analytics_worker") -> None:
        """Move the analytics consumer group back to the start of a stream (XGROUP SETID 0).

        Every message in the stream is delivered again to the running consumer.
        """
        asyncio.run(self.redis.xgroup_setid(stream, group, "0"))

    def grant_view(self, campaign_id: str, user_id: str = SERVICE_SUBJECT) -> None:
        """Grant a spectator (the schema relation behind `campaign.view`) on a campaign.

        Campaign Analytics has no membership frontdoor, so the relation is written in the
        authorization double. Only schema relation names are written.
        """
        asyncio.run(
            self.spicedb.write_relationship(
                resource_type="campaign",
                resource_id=str(campaign_id),
                relation="spectator",
                subject_type="user",
                subject_id=user_id,
            )
        )

    def start(self, *, authenticated: bool = True) -> TestClient:
        """Return a client whose context manager runs the service lifespan.

        Requests carry the member's bearer token unless `authenticated` is False.
        """
        headers = bearer(SERVICE_SUBJECT) if authenticated else None
        return TestClient(create_app_from_environment(), headers=headers)


@pytest.fixture
def analytics_service(
    postgres_service: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> Iterator[AnalyticsService]:
    """Point the service at the PostgreSQL container and the Redis double for one test."""

    dsn = str(postgres_service["async_dsn"])
    monkeypatch.setenv("RUNEFOBLE_DATABASE_URL", dsn)

    double = MockAsyncRedis()
    monkeypatch.setattr(redis.asyncio, "from_url", lambda *_a, **_k: double)

    spicedb = MockSpiceDBClient()
    with (
        shared_spicedb_client(spicedb),
        restored_seam(get_event_store, set_event_store, None, replace=True),
    ):
        yield AnalyticsService(dsn=dsn, redis=double, spicedb=spicedb)
