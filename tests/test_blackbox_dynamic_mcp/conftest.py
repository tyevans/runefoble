"""Test fixtures for dynamic FastMCP blackbox tests.

Routes under /mcp/tools take the caller only from a verified bearer token (TASK-0532).
The default `client` sends a signed token for `user-test`. Tests that act as another
user pass their own Authorization header per request.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from gateway_mcp.dynamic import (
    dynamic_registry,
)
from gateway_mcp.routers import build_tools_registry_router
from gateway_mcp.server import mcp
from runefoble_auth.principal import require_principal
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.redis_bus import RedisStreamsEventBus

from tests.helpers.mcp_http import serve_mcp
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import SIGNING_ISSUER

CALLER_VERIFIER = SIGNING_ISSUER.verifier()


def caller_headers(sub: str) -> dict[str, str]:
    """Return the Authorization header for a token that the shared test issuer signs for `sub`."""
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


@pytest.fixture
def mock_redis() -> MockAsyncRedis:
    return MockAsyncRedis()


@pytest.fixture
def event_bus(mock_redis: MockAsyncRedis, use_redis_client) -> RedisStreamsEventBus:
    bus = use_redis_client(mock_redis)
    return bus


@pytest.fixture
def test_app() -> FastAPI:
    app = FastAPI(title="FastMCP Dynamic Registry Test App")
    app.include_router(build_tools_registry_router(require_principal(lambda: CALLER_VERIFIER)))
    return app


@pytest.fixture
def client(
    test_app: FastAPI, spicedb: MockSpiceDBClient, event_bus: RedisStreamsEventBus
) -> TestClient:
    return TestClient(test_app, headers=caller_headers("user-test"))


@pytest.fixture
def anonymous_client(
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


@pytest.fixture(scope="module")
def mcp_endpoint() -> Iterator[str]:
    """Serve the gateway MCP server over HTTP. The endpoint trusts the shared signing issuer."""
    with serve_mcp(mcp) as endpoint:
        yield endpoint
