"""Start the Campaign Analytics service on a real PostgreSQL container and a Redis double.

PostgreSQL is the container from the `postgres_service` fixture. Redis is an external process,
so the double replaces only the redis.asyncio client at the connection boundary. The service
starts through its real lifespan. Each `start()` call is a new process-equivalent start, so a
second start after the first one exits is a restart.

Governed by ADR-0011, ADR-0015, and Hard Invariant 7 (events in and HTTP reads out).
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any

import pytest
import redis.asyncio
from fastapi.testclient import TestClient
from runefoble_auth.mock_spicedb import MockSpiceDBClient
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_sourcing import set_event_store
from runefoble_platform.redis_bus import RedisStreamsEventBus

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import SIGNING_ISSUER

SESSION_STREAM = "runefoble.events.session"
BOARD_STREAM = "runefoble.events.board"
CHARACTER_STREAM = "runefoble.events.character"
WATCHER_STREAM = "runefoble.events.watcher"

SERVICE_SUBJECT = "user-test"


def bearer(sub: str) -> dict[str, str]:
    """Return the Authorization header for a token that the shared test issuer signs for `sub`."""
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


def wait_until(predicate: Callable[[], bool], timeout_s: float = 10.0) -> bool:
    """Poll until the predicate holds or the timeout passes."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return predicate()


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
        """Grant a member view rights on a campaign in the authorization double."""
        asyncio.run(
            self.spicedb.write_relationship(
                resource_type="campaign",
                resource_id=str(campaign_id),
                relation="view",
                subject_type="user",
                subject_id=user_id,
            )
        )

    def start(self, *, authenticated: bool = True) -> TestClient:
        """Return a client whose context manager runs the service lifespan.

        Requests carry the member's bearer token unless `authenticated` is False.
        """
        from campaign_analytics.main import app

        headers = bearer(SERVICE_SUBJECT) if authenticated else None
        return TestClient(app, headers=headers)


@pytest.fixture
def analytics_service(
    postgres_service: dict[str, Any] | None, monkeypatch: pytest.MonkeyPatch
) -> Iterator[AnalyticsService]:
    """Point the service at the PostgreSQL container and the Redis double for one test."""
    if not postgres_service:
        pytest.skip("Docker not available for the Campaign Analytics PostgreSQL store")

    import campaign_analytics.main as analytics_main
    from campaign_analytics.dependencies import get_spicedb_client, set_spicedb_client

    dsn = str(postgres_service["async_dsn"])
    monkeypatch.setenv("RUNEFOBLE_DATABASE_URL", dsn)
    monkeypatch.setattr(analytics_main, "platform_settings", PlatformSettings())

    double = MockAsyncRedis()
    monkeypatch.setattr(redis.asyncio, "from_url", lambda *_a, **_k: double)

    spicedb = MockSpiceDBClient()
    previous_spicedb = get_spicedb_client()
    set_spicedb_client(spicedb)
    set_event_store(None)
    try:
        yield AnalyticsService(dsn=dsn, redis=double, spicedb=spicedb)
    finally:
        set_spicedb_client(previous_spicedb)
        set_event_store(None)
