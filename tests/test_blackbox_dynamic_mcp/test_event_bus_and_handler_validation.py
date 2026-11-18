"""Blackbox tests for dynamic MCP event delivery and handler-less tool rejection.

Dynamic tool events must reach the Redis Streams bus that the gateway injects at
startup. Events must never disappear silently, and a tool without a handler must
never register.
"""

from __future__ import annotations

import asyncio
import logging

import pytest
from fastapi.testclient import TestClient
from gateway_mcp.dynamic import (
    DynamicToolDefinition,
    DynamicToolRegistry,
    get_event_bus,
)
from gateway_mcp.dynamic.events import publish_system_event
from gateway_mcp.server import mcp
from runefoble_events.events import DynamicToolUnregisteredEvent
from runefoble_platform.config import PlatformSettings
from runefoble_platform.redis_bus import RedisStreamsEventBus

EVENTS_LOGGER = "runefoble.gateway_mcp.dynamic.events"


class _UnreachableRedisClient:
    """Stands in for a Redis server that refuses connections (external process boundary)."""

    async def xadd(self, stream: str, fields: dict[str, str]) -> str:
        raise ConnectionError("redis unreachable")


def _handler_less_payload(name: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": name,
        "description": "Tool without logic",
        "parameters": {"type": "object", "properties": {}},
    }
    payload.update(overrides)
    return payload


@pytest.mark.parametrize(
    "overrides",
    [{"handler": None}, {"handler": {}}, {"handler": "   "}, {}],
    ids=["null", "empty", "blank", "missing"],
)
def test_blackbox_register_rejects_tool_without_handler(client: TestClient, overrides):
    """A definition with no handler is rejected with 422 and no tool is added."""
    name = "handler_less_probe"

    res = client.post("/mcp/tools/register", json=_handler_less_payload(name, **overrides))

    assert res.status_code == 422
    assert mcp._tool_manager.get_tool(name) is None
    assert client.get(f"/mcp/tools/{name}").status_code == 404


def test_blackbox_gateway_mcp_startup_injects_redis_streams_bus():
    """Gateway startup injects the Redis Streams bus that dynamic tool events use."""
    from gateway_mcp.server import configure_dynamic_event_bus

    configure_dynamic_event_bus(PlatformSettings(redis_url="redis://redis.example:6379/3"))
    bus = get_event_bus()

    assert isinstance(get_event_bus(), RedisStreamsEventBus)
    assert bus.redis_url == "redis://redis.example:6379/3"


def test_blackbox_gateway_mcp_startup_refuses_missing_redis_url():
    """Gateway startup fails when no Redis URL exists, so no tool runs without a bus."""
    from gateway_mcp.server import configure_dynamic_event_bus

    with pytest.raises(RuntimeError, match="REDIS_URL"):
        configure_dynamic_event_bus(PlatformSettings(redis_url=""))


def test_blackbox_publish_failure_is_logged(caplog: pytest.LogCaptureFixture, use_redis_client):
    """A failed publish is logged as an error with the event type and cause."""
    use_redis_client(_UnreachableRedisClient())
    event = DynamicToolUnregisteredEvent(tool_name="probe", unregistered_by=None, campaign_id=None)

    with caplog.at_level(logging.ERROR, logger=EVENTS_LOGGER):
        asyncio.run(publish_system_event(event))

    assert "DynamicToolUnregisteredEvent" in caplog.text
    assert "redis unreachable" in caplog.text


def test_blackbox_publish_without_bus_is_logged(caplog: pytest.LogCaptureFixture, use_event_bus):
    """An event with no injected bus is logged as dropped, never swallowed."""
    use_event_bus(None)
    event = DynamicToolUnregisteredEvent(tool_name="probe", unregistered_by=None, campaign_id=None)

    with caplog.at_level(logging.ERROR, logger=EVENTS_LOGGER):
        asyncio.run(publish_system_event(event))

    assert "DynamicToolUnregisteredEvent" in caplog.text
    assert "not configured" in caplog.text


def test_blackbox_registration_without_event_loop_is_logged(caplog: pytest.LogCaptureFixture):
    """A registration outside a running loop logs the event it could not dispatch."""
    registry = DynamicToolRegistry()
    definition = DynamicToolDefinition(name="sync_probe", handler={"ok": True})

    with caplog.at_level(logging.ERROR, logger=EVENTS_LOGGER):
        registry.register_tool(definition, author_id="sync-author")

    assert "DynamicToolRegisteredEvent" in caplog.text
    assert "no running event loop" in caplog.text
