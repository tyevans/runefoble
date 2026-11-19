"""Blackbox tests: the tool admin routes run in the MCP process (TASK-0727).

A tool registered through the public admin route must show up for MCP clients. The API
gateway no longer serves the admin routes, because it cannot reach the MCP registry.
"""

from __future__ import annotations

import asyncio

import httpx
from fastapi.testclient import TestClient
from gateway_api.main import app as api_app

from tests.helpers.mcp_http import mcp_session
from tests.helpers.ws_identity import SIGNING_ISSUER

TOOL = {
    "name": "process_probe_tool",
    "description": "Triples a number.",
    "parameters": {"type": "object", "properties": {"n": {"type": "integer"}}, "required": ["n"]},
    "handler": {"tripled": {"$expr": "n * 3"}},
}


def _tool_names(endpoint: str, bearer: str) -> list[str]:
    async def run() -> list[str]:
        async with mcp_session(endpoint, bearer) as session:
            return [t.name for t in (await session.list_tools()).tools]

    return asyncio.run(run())


def test_registered_tool_is_listed_and_callable_over_mcp(mcp_endpoint: str):
    token = SIGNING_ISSUER.mint("alice")
    base = mcp_endpoint.removesuffix("/mcp")
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(base_url=base, headers=headers) as http:
        assert http.post("/mcp/tools/register", json=TOOL).status_code == 200
        assert TOOL["name"] in _tool_names(mcp_endpoint, token)

        async def call():
            async with mcp_session(mcp_endpoint, token) as session:
                return await session.call_tool(TOOL["name"], {"n": 4})

        result = asyncio.run(call())
        assert result.isError is False
        assert "12" in str(result.content[0].text)

        assert http.delete(f"/mcp/tools/{TOOL['name']}").status_code == 200
        assert TOOL["name"] not in _tool_names(mcp_endpoint, token)


def test_admin_routes_need_a_bearer_on_the_mcp_process(mcp_endpoint: str):
    base = mcp_endpoint.removesuffix("/mcp")
    assert httpx.get(f"{base}/mcp/tools/dynamic").status_code == 401


def test_mcp_process_publishes_its_openapi_spec(mcp_endpoint: str):
    token = SIGNING_ISSUER.mint("alice")
    spec = httpx.get(
        f"{mcp_endpoint.removesuffix('/mcp')}/openapi.json",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert spec.status_code == 200
    assert "/mcp/tools/register" in spec.json()["paths"]


def test_api_gateway_no_longer_serves_the_tool_routes():
    token = SIGNING_ISSUER.mint("alice")
    headers = {"Authorization": f"Bearer {token}"}
    with TestClient(api_app) as gateway:
        for path in ("/mcp/tools", "/mcp/tools/dynamic"):
            assert gateway.get(path, headers=headers).status_code == 404
            assert gateway.post(f"{path}/register", json=TOOL, headers=headers).status_code == 404
