"""Call the gateway MCP server over its streamable HTTP transport, as an MCP client does.

The HTTP transport carries the caller's `Authorization` header on each MCP request.
The gateway forwards that bearer to the owning services, so these helpers make the
caller identity part of the MCP request itself. In-memory sessions carry no headers.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from typing import Any

import httpx
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.server import StreamableHTTPASGIApp
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.shared.exceptions import McpError
from mcp.types import CallToolResult
from pydantic import AnyUrl
from starlette.applications import Starlette
from starlette.routing import Route

from tests.helpers.live_services import serve


def _mcp_http_app(server: FastMCP) -> Starlette:
    """Return a fresh streamable HTTP app for `server`.

    FastMCP caches one session manager, and a manager runs only once. Each test module
    therefore gets its own manager over the same protocol server.
    """
    manager = StreamableHTTPSessionManager(app=server._mcp_server)

    @asynccontextmanager
    async def _lifespan(_: Starlette) -> AsyncIterator[None]:
        async with manager.run():
            yield

    routes = [
        Route("/mcp", endpoint=StreamableHTTPASGIApp(manager), methods=["GET", "POST", "DELETE"])
    ]
    return Starlette(routes=routes, lifespan=_lifespan)


@contextmanager
def serve_mcp(server: FastMCP) -> Iterator[str]:
    """Serve `server` on a free loopback port and yield its MCP endpoint URL."""
    with serve(_mcp_http_app(server), lifespan="on") as base_url:
        yield f"{base_url}/mcp"


@asynccontextmanager
async def mcp_session(endpoint: str, bearer: str | None = None) -> AsyncIterator[ClientSession]:
    """Open an initialized MCP client session that sends `bearer` on every request."""
    headers = {"Authorization": f"Bearer {bearer}"} if bearer else {}
    async with (
        httpx.AsyncClient(headers=headers) as http_client,
        streamable_http_client(endpoint, http_client=http_client) as (read, write, _),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        yield session


async def call_tool_over_http(
    endpoint: str, name: str, arguments: dict[str, Any], bearer: str | None = None
) -> CallToolResult:
    """Call one MCP tool through the HTTP transport, with the caller bearer if given."""
    async with mcp_session(endpoint, bearer) as session:
        return await session.call_tool(name, arguments)


async def read_resource_over_http(endpoint: str, uri: str, bearer: str | None = None) -> str:
    """Read one MCP resource through the HTTP transport and return its first text body."""
    try:
        async with mcp_session(endpoint, bearer) as session:
            result = await session.read_resource(AnyUrl(uri))
    except BaseExceptionGroup as group:
        # The task groups wrap an MCP error in one or more groups. Unwrap to the MCP error.
        leaf: BaseException = group
        while isinstance(leaf, BaseExceptionGroup):
            leaf = leaf.exceptions[0]
        if not isinstance(leaf, McpError):
            raise
        raise leaf from None
    return str(result.contents[0].text)
