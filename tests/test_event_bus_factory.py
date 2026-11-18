"""Blackbox start-up tests for the shared Redis Streams event bus (ADR-0015 item 4).

With Redis configured and unreachable, start-up must fail. No in-memory bus is returned.
A service app starts through its public lifespan. The tests use a real board_state app.
"""

import pytest
from board_state.dependencies import event_bus_provider as board_provider
from board_state.main import app as board_app
from fastapi.testclient import TestClient
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_bus import EventBusProvider, EventBusUnavailableError
from runefoble_platform.redis_bus import RedisStreamsEventBus


@pytest.mark.asyncio
async def test_start_up_fails_when_redis_is_unreachable():
    provider = EventBusProvider(PlatformSettings(redis_url="redis://127.0.0.1:1/0"))

    with pytest.raises(EventBusUnavailableError, match="unreachable at start-up"):
        async with provider.lifespan(None):
            pass


@pytest.mark.asyncio
async def test_start_up_fails_when_redis_url_is_empty():
    provider = EventBusProvider(PlatformSettings(redis_url=""))

    with pytest.raises(EventBusUnavailableError, match="is empty"):
        async with provider.lifespan(None):
            pass


def test_service_app_does_not_start_when_redis_is_unreachable(default_redis_event_bus):
    board_provider.set(RedisStreamsEventBus(redis_url="redis://127.0.0.1:1/0"))

    with (
        pytest.raises(EventBusUnavailableError, match="unreachable at start-up"),
        TestClient(board_app),
    ):
        pass


def test_service_app_starts_when_redis_answers(default_redis_event_bus):
    board_provider.set(default_redis_event_bus)

    with TestClient(board_app) as client:
        assert client.get("/healthz").status_code == 200
