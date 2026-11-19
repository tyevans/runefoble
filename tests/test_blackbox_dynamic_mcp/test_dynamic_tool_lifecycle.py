"""Blackbox tests verifying dynamic FastMCP tool lifecycle, discovery, execution, and CloudEvents."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.helpers.mcp_http import call_tool_json, listed_tools
from tests.helpers.ws_identity import SIGNING_ISSUER


@pytest.mark.asyncio
async def test_blackbox_register_dynamic_tool_and_discovery(client: TestClient, mcp_endpoint: str):
    """Verify registering a dynamic tool via POST /mcp/tools/register and reflection in FastMCP."""
    tool_name = "calculate_falloff"
    payload = {
        "name": tool_name,
        "description": "Calculates spell falloff damage over distance",
        "parameters": {
            "type": "object",
            "properties": {
                "base_damage": {"type": "integer", "description": "Initial damage value"},
                "distance": {"type": "integer", "description": "Target distance in tiles"},
            },
            "required": ["base_damage", "distance"],
        },
        "handler": {
            "effective_damage": {"$expr": "max(0, base_damage - (distance * 2))"},
            "distance": "${distance}",
        },
        "metadata": {"version": "1.0.0", "author": "modder-1"},
    }

    # 1. Register tool via public HTTP frontdoor
    res = client.post("/mcp/tools/register", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "registered"
    assert data["tool"]["name"] == tool_name

    # 2. Query dynamic tool catalog
    list_res = client.get("/mcp/tools/dynamic")
    assert list_res.status_code == 200
    tool_names = [t["name"] for t in list_res.json()["tools"]]
    assert tool_name in tool_names

    # 3. Verify FastMCP public protocol discovers new tool without restart
    fastmcp_tool = (await listed_tools(mcp_endpoint)).get(tool_name)
    assert fastmcp_tool is not None, "Tool must be discovered in FastMCP immediately"
    assert "base_damage" in fastmcp_tool.inputSchema["properties"]
    assert "distance" in fastmcp_tool.inputSchema["properties"]

    # 4. Invoke via FastMCP protocol entrypoint
    mcp_out = await call_tool_json(
        mcp_endpoint,
        tool_name,
        {"base_damage": 30, "distance": 5},
        SIGNING_ISSUER.mint("user-test"),
    )
    assert mcp_out["effective_damage"] == 20
    assert mcp_out["distance"] == 5

    # 5. Invoke via REST administrative execution frontdoor
    exec_res = client.post(
        f"/mcp/tools/{tool_name}/execute", json={"arguments": {"base_damage": 50, "distance": 10}}
    )
    assert exec_res.status_code == 200
    assert exec_res.json()["result"]["effective_damage"] == 30


@pytest.mark.asyncio
async def test_blackbox_deregister_dynamic_tool(client: TestClient, mcp_endpoint: str):
    """Verify unregistering a dynamic tool removes it from REST catalog and FastMCP server."""
    tool_name = "temporary_blessing"
    payload = {
        "name": tool_name,
        "description": "Temporary buff",
        "parameters": {"type": "object", "properties": {"bonus": {"type": "integer"}}},
        "handler": {"bonus": "${bonus}"},
    }
    # Register tool
    client.post("/mcp/tools/register", json=payload)
    assert (await listed_tools(mcp_endpoint)).get(tool_name) is not None

    # Deregister tool
    del_res = client.delete(f"/mcp/tools/{tool_name}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deregistered"

    # Verify tool is gone from FastMCP and dynamic list
    assert (await listed_tools(mcp_endpoint)).get(tool_name) is None
    list_res = client.get("/mcp/tools/dynamic")
    tool_names = [t["name"] for t in list_res.json()["tools"]]
    assert tool_name not in tool_names

    # Deleting nonexistent tool returns 404
    missing_res = client.delete(f"/mcp/tools/{tool_name}")
    assert missing_res.status_code == 404
