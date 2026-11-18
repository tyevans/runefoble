"""Test fixtures for dynamic FastMCP blackbox tests."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from gateway_mcp.dynamic import (
    dynamic_registry,
    set_event_bus,
    set_spicedb_client,
)
from gateway_mcp.routers import tools_registry_router
from gateway_mcp.server import mcp
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.redis_bus import RedisStreamsEventBus

from tests.helpers.mock_redis import MockAsyncRedis


@pytest.fixture
def mock_redis() -> MockAsyncRedis:
    return MockAsyncRedis()


@pytest.fixture
def event_bus(mock_redis: MockAsyncRedis) -> RedisStreamsEventBus:
    bus = RedisStreamsEventBus(client=mock_redis)
    set_event_bus(bus)
    return bus


@pytest.fixture
def test_app() -> FastAPI:
    app = FastAPI(title="FastMCP Dynamic Registry Test App")
    app.include_router(tools_registry_router)
    return app


@pytest.fixture
def client(
    test_app: FastAPI, spicedb: MockSpiceDBClient, event_bus: RedisStreamsEventBus
) -> TestClient:
    return TestClient(test_app)


@pytest.fixture(autouse=True)
def clean_registry(spicedb: MockSpiceDBClient, event_bus: RedisStreamsEventBus):
    """Ensure clean registry and FastMCP server before and after each test."""
    dynamic_registry.set_mcp_server(mcp)
    for tool_def in list(dynamic_registry.list_tools()):
        dynamic_registry.deregister_tool(tool_def.name)
    yield
    for tool_def in list(dynamic_registry.list_tools()):
        dynamic_registry.deregister_tool(tool_def.name)
    set_spicedb_client(None)
    set_event_bus(None)
