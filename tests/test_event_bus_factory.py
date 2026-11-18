"""Blackbox start-up tests for the shared Redis Streams event bus (ADR-0015 item 4).

With Redis configured and unreachable, start-up must fail. No in-memory bus is returned.
"""

import pytest
from fastapi import FastAPI
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_bus import EventBusUnavailableError, event_bus_lifespan


@pytest.mark.asyncio
async def test_start_up_fails_when_redis_is_unreachable():
    app = FastAPI()
    settings = PlatformSettings(redis_url="redis://127.0.0.1:1/0")

    with pytest.raises(EventBusUnavailableError, match="unreachable at start-up"):
        async with event_bus_lifespan(app, settings):
            pass

    assert getattr(app.state, "event_bus", None) is None


@pytest.mark.asyncio
async def test_start_up_fails_when_redis_url_is_empty():
    app = FastAPI()
    settings = PlatformSettings(redis_url="")

    with pytest.raises(EventBusUnavailableError, match="is empty"):
        async with event_bus_lifespan(app, settings):
            pass
