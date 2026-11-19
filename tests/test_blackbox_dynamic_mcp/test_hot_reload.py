"""Blackbox tests verifying hot-reloading of dynamic tool logic and schema."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.helpers.mcp_http import call_tool_json, listed_tools
from tests.helpers.ws_identity import SIGNING_ISSUER


@pytest.mark.asyncio
async def test_blackbox_hot_reload_tool_logic_without_restart(
    client: TestClient, mcp_endpoint: str
):
    """Verify tool logic and schema can be hot-reloaded dynamically without restarting server."""
    tool_name = "dynamic_stealth_check"

    # 1. Initial version
    v1_payload = {
        "name": tool_name,
        "description": "Stealth check v1",
        "parameters": {
            "type": "object",
            "properties": {"dex_mod": {"type": "integer"}},
            "required": ["dex_mod"],
        },
        "handler": {"total": {"$expr": "10 + dex_mod"}, "version": 1},
    }
    res1 = client.post("/mcp/tools/register", json=v1_payload)
    assert res1.status_code == 200

    tool_v1 = (await listed_tools(mcp_endpoint)).get(tool_name)
    assert tool_v1 is not None
    out1 = await call_tool_json(
        mcp_endpoint, tool_name, {"dex_mod": 3}, SIGNING_ISSUER.mint("user-test")
    )
    assert out1["total"] == 13
    assert out1["version"] == 1

    # 2. Hot-reload with v2 logic (adds proficiency parameter)
    v2_payload = {
        "name": tool_name,
        "description": "Stealth check v2 with proficiency",
        "parameters": {
            "type": "object",
            "properties": {
                "dex_mod": {"type": "integer"},
                "prof_bonus": {"type": "integer", "default": 2},
            },
            "required": ["dex_mod"],
        },
        "handler": {"total": {"$expr": "10 + dex_mod + prof_bonus"}, "version": 2},
    }
    res2 = client.put(f"/mcp/tools/{tool_name}", json=v2_payload)
    assert res2.status_code == 200
    assert res2.json()["status"] == "updated"

    # 3. Assert FastMCP immediately runs updated logic without server restart
    tool_v2 = (await listed_tools(mcp_endpoint)).get(tool_name)
    assert "prof_bonus" in tool_v2.inputSchema["properties"]
    out2 = await call_tool_json(
        mcp_endpoint, tool_name, {"dex_mod": 3, "prof_bonus": 4}, SIGNING_ISSUER.mint("user-test")
    )
    assert out2["total"] == 17
    assert out2["version"] == 2


def test_blackbox_invalid_parameter_schema_rejection(client: TestClient):
    """Verify malformed parameter schemas are rejected cleanly."""
    # Top-level is not object
    bad_schema_1 = {
        "name": "bad_tool_1",
        "parameters": {"type": "array", "items": {"type": "string"}},
        "handler": {"ok": True},
    }
    res1 = client.post("/mcp/tools/register", json=bad_schema_1)
    assert res1.status_code == 400
    assert "object" in res1.json()["detail"].lower()

    # Invalid JSON Schema
    bad_schema_2 = {
        "name": "bad_tool_2",
        "parameters": {"type": "object", "properties": "invalid_not_dict"},
        "handler": {"ok": True},
    }
    res2 = client.post("/mcp/tools/register", json=bad_schema_2)
    assert res2.status_code == 400
