"""Blackbox tests verifying dynamic FastMCP tool lifecycle, discovery, execution, and CloudEvents."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from gateway_mcp.server import mcp
from runefoble_platform.consumer_group import MockAsyncRedis


@pytest.mark.asyncio
async def test_blackbox_register_dynamic_tool_and_discovery(client: TestClient):
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
        "handler_code": (
            "def handle(base_damage: int, distance: int) -> dict:\n"
            "    reduced = max(0, base_damage - (distance * 2))\n"
            "    return {'effective_damage': reduced, 'distance': distance}\n"
        ),
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
    fastmcp_tool = mcp.get_tool(tool_name)
    assert fastmcp_tool is not None, "Tool must be discovered in FastMCP immediately"
    assert "base_damage" in fastmcp_tool.parameters["properties"]
    assert "distance" in fastmcp_tool.parameters["properties"]

    # 4. Invoke via FastMCP protocol entrypoint
    mcp_out = await fastmcp_tool.run({"base_damage": 30, "distance": 5})
    assert mcp_out["effective_damage"] == 20
    assert mcp_out["distance"] == 5

    # 5. Invoke via REST administrative execution frontdoor
    exec_res = client.post(
        f"/mcp/tools/{tool_name}/execute", json={"arguments": {"base_damage": 50, "distance": 10}}
    )
    assert exec_res.status_code == 200
    assert exec_res.json()["result"]["effective_damage"] == 30


@pytest.mark.asyncio
async def test_blackbox_deregister_dynamic_tool(client: TestClient):
    """Verify unregistering a dynamic tool removes it from REST catalog and FastMCP server."""
    tool_name = "temporary_blessing"
    payload = {
        "name": tool_name,
        "description": "Temporary buff",
        "parameters": {"type": "object", "properties": {"bonus": {"type": "integer"}}},
        "handler_code": "def handle(bonus: int = 1): return {'bonus': bonus}",
    }
    # Register tool
    client.post("/mcp/tools/register", json=payload)
    assert mcp.get_tool(tool_name) is not None

    # Deregister tool
    del_res = client.delete(f"/mcp/tools/{tool_name}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deregistered"

    # Verify tool is gone from FastMCP and dynamic list
    assert mcp.get_tool(tool_name) is None
    list_res = client.get("/mcp/tools/dynamic")
    tool_names = [t["name"] for t in list_res.json()["tools"]]
    assert tool_name not in tool_names

    # Deleting nonexistent tool returns 404
    missing_res = client.delete(f"/mcp/tools/{tool_name}")
    assert missing_res.status_code == 404


@pytest.mark.asyncio
async def test_blackbox_tool_lifecycle_cloudevents(client: TestClient, mock_redis: MockAsyncRedis):
    """Verify tool registration, invocation, and unregistration emit domain events to Redis Stream."""
    stream_name = "runefoble:events:system"
    tool_name = "alchemical_elixir"
    payload = {
        "name": tool_name,
        "description": "Brew elixir",
        "parameters": {"type": "object", "properties": {"potency": {"type": "integer"}}},
        "handler_code": "def handle(potency: int = 2): return {'healed': potency * 5}",
        "metadata": {"category": "alchemy"},
    }

    # Register
    client.post("/mcp/tools/register", json=payload, headers={"X-User-Id": "gm-evelyn"})

    # Execute
    client.post(
        f"/mcp/tools/{tool_name}/execute",
        json={"arguments": {"potency": 4}},
        headers={"X-User-Id": "gm-evelyn"},
    )

    # Deregister
    client.delete(f"/mcp/tools/{tool_name}", headers={"X-User-Id": "gm-evelyn"})

    # Inspect messages published to Redis Stream
    stream_messages = mock_redis.streams.get(stream_name, [])
    assert len(stream_messages) >= 3

    event_types = [fields.get("event_type") for _, fields in stream_messages]
    assert "DynamicToolRegistered" in event_types
    assert "DynamicToolInvoked" in event_types
    assert "DynamicToolUnregistered" in event_types

    # Verify payload details for registration
    reg_fields = next(
        fields
        for _, fields in stream_messages
        if fields.get("event_type") == "DynamicToolRegistered"
    )
    reg_payload = json.loads(reg_fields["payload"])
    assert reg_payload["tool_name"] == tool_name
    assert reg_payload["author_id"] == "gm-evelyn"
