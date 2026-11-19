"""Test fixtures for dynamic FastMCP blackbox tests.

Routes under /mcp/tools take the caller only from a verified bearer token (TASK-0532).
The default `client` sends a signed token for `user-test`. Tests that act as another
user pass their own Authorization header per request.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from gateway_mcp.container import GatewayMcpContainer
from gateway_mcp.identity import BearerTransportAuth
from runefoble_auth.mock import MockSpiceDBClient
from runefoble_platform.redis_bus import RedisStreamsEventBus

from tests.helpers.mcp_http import mcp_http_app, serve_mcp
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import SIGNING_ISSUER


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
def container() -> GatewayMcpContainer:
    """A fresh gateway container for one test. No registry state carries over between tests."""
    return GatewayMcpContainer.default()


@pytest.fixture
def test_app(container: GatewayMcpContainer) -> BearerTransportAuth:
    """The MCP app as the gateway-mcp process serves it: bearer check, `/mcp`, tool routes."""
    return mcp_http_app(container)


@pytest.fixture
def client(
    test_app: BearerTransportAuth, spicedb: MockSpiceDBClient, event_bus: RedisStreamsEventBus
) -> TestClient:
    return TestClient(test_app, headers=caller_headers("user-test"))


@pytest.fixture
def anonymous_client(
    test_app: BearerTransportAuth, spicedb: MockSpiceDBClient, event_bus: RedisStreamsEventBus
) -> TestClient:
    return TestClient(test_app)


@pytest.fixture
def mcp_endpoint(container: GatewayMcpContainer) -> Iterator[str]:
    """Serve this test's gateway app over HTTP. The endpoint trusts the shared signing issuer."""
    with serve_mcp(container) as endpoint:
        yield endpoint
