"""Blackbox tests for event bus selection at start-up (ADR-0015 item 4).

With the Redis flag set, a failed bus initialization must raise. It must never return
an in-memory bus. With the flag off, the in-memory bus is the local test mode.
"""

import pytest
from eventsource.adapters.memory.bus import InMemoryEventBus
from eventsource.adapters.redis.bus import RedisEventBus
from redis.exceptions import ConnectionError as RedisConnectionError
from runefoble_platform import event_sourcing
from runefoble_platform.config import PlatformSettings


class RedisBusSettings(PlatformSettings):
    use_redis_event_bus: bool = True


class InMemoryBusSettings(PlatformSettings):
    use_redis_event_bus: bool = False


@pytest.fixture(autouse=True)
def _reset_global_bus():
    event_sourcing.set_event_bus(None)
    yield
    event_sourcing.set_event_bus(None)


def test_flag_off_returns_in_memory_bus():
    bus = event_sourcing.get_event_bus(InMemoryBusSettings())

    assert isinstance(bus, InMemoryEventBus)


def test_flag_on_returns_redis_bus():
    bus = event_sourcing.get_event_bus(RedisBusSettings(redis_url="redis://127.0.0.1:1/0"))

    assert isinstance(bus, RedisEventBus)


def test_flag_on_initialization_failure_propagates_without_in_memory_fallback(monkeypatch):
    def unreachable(**_kwargs):
        raise RedisConnectionError("Error 111 connecting to 127.0.0.1:1")

    monkeypatch.setattr(event_sourcing, "RedisEventBus", unreachable)

    with pytest.raises(RedisConnectionError):
        event_sourcing.get_event_bus(RedisBusSettings(redis_url="redis://127.0.0.1:1/0"))

    assert event_sourcing._global_event_bus is None
