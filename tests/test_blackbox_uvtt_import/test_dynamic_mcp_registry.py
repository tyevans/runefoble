"""Blackbox integration tests for dynamic FastMCP tool registration and sandboxing.

Governed by TASK-0193 and ADR-0008.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from gateway_mcp.server import mcp


@pytest.mark.asyncio
async def test_blackbox_dynamic_mcp_tool_registration_and_execution(gateway_client: TestClient):
    """Verify registering a dynamic tool via administrative frontdoor and invoking it in FastMCP."""
    tool_name = "calculate_spell_falloff"
    assert mcp.get_tool(tool_name) is None

    # Register dynamic tool definition via administrative HTTP frontdoor
    tool_payload = {
        "name": tool_name,
        "description": "Calculates spell damage dropoff across tactical grid distance",
        "parameters": {
            "type": "object",
            "properties": {
                "base_damage": {"type": "integer", "description": "Base spell damage"},
                "distance": {"type": "integer", "description": "Hex or grid distance in units"},
            },
            "required": ["base_damage", "distance"],
        },
        "handler_code": (
            "def handle(base_damage: int, distance: int) -> dict:\n"
            "    penalty = max(0, distance * 2)\n"
            "    effective_damage = max(0, base_damage - penalty)\n"
            "    return {'effective_damage': effective_damage, 'reduced_by': penalty}\n"
        ),
        "sandbox_policy": {"allowed_modules": ["math"]},
        "metadata": {"author": "Alex (Modder)", "version": "1.0.0"},
    }

    reg_resp = gateway_client.post("/mcp/tools", json=tool_payload)
    assert reg_resp.status_code == 200, reg_resp.text
    assert reg_resp.json()["status"] == "registered"

    # Assert tool is immediately visible in FastMCP discovery WITHOUT gateway restart
    registered_tool = mcp.get_tool(tool_name)
    assert registered_tool is not None, "Tool must be discovered immediately in FastMCP"
    assert "base_damage" in registered_tool.parameters["properties"]
    assert "distance" in registered_tool.parameters["properties"]

    # Invoke the dynamic tool through public FastMCP tool interface
    mcp_result = await registered_tool.run({"base_damage": 25, "distance": 4})
    assert mcp_result["effective_damage"] == 17
    assert mcp_result["reduced_by"] == 8

    # Invoke through administrative HTTP execution frontdoor
    exec_resp = gateway_client.post(
        f"/mcp/tools/{tool_name}/execute",
        json={"arguments": {"base_damage": 30, "distance": 10}},
    )
    assert exec_resp.status_code == 200
    res_data = exec_resp.json()
    assert res_data["status"] == "success"
    assert res_data["result"]["effective_damage"] == 10
    assert res_data["result"]["reduced_by"] == 20

    # Listing dynamic tools endpoint
    list_resp = gateway_client.get("/mcp/tools")
    assert list_resp.status_code == 200
    tool_names = [t["name"] for t in list_resp.json()["tools"]]
    assert tool_name in tool_names


def test_blackbox_dynamic_mcp_sandbox_rejection_security(gateway_client: TestClient):
    """Verify sandbox policies reject dangerous system calls or restricted imports."""
    unsafe_cases = [
        ("os", "import os\ndef handle(): return os.getcwd()"),
        ("subprocess", "import subprocess\ndef handle(): return subprocess.run('ls')"),
        ("open", "def handle():\n    with open('/etc/passwd') as f: return f.read()"),
        ("dunder", "def handle(): return ().__class__.__bases__[0].__subclasses__()"),
    ]
    for tag, code in unsafe_cases:
        name = f"malicious_tool_{tag}"
        payload = {
            "name": name,
            "parameters": {"type": "object", "properties": {}},
            "handler_code": code,
        }
        resp = gateway_client.post("/mcp/tools", json=payload)
        assert resp.status_code == 400, f"Expected rejection for {name}"
        assert "Sandbox policy violation" in resp.json()["detail"]
        assert mcp.get_tool(name) is None


def test_blackbox_dynamic_mcp_tool_lifecycle(gateway_client: TestClient):
    """Verify updating and deregistering dynamic tools cleanly."""
    tool_name = "tactical_flare"
    initial_payload = {
        "name": tool_name,
        "description": "Launch illumination flare",
        "parameters": {
            "type": "object",
            "properties": {"radius": {"type": "integer"}},
            "required": ["radius"],
        },
        "handler_code": "def handle(radius: int) -> dict: return {'illuminated_radius': radius}",
    }

    # Register tool
    reg = gateway_client.post("/mcp/tools", json=initial_payload)
    assert reg.status_code == 200
    assert mcp.get_tool(tool_name) is not None

    # Update tool with new description and parameters
    update_payload = {
        "name": tool_name,
        "description": "Launch enhanced illumination flare with color",
        "parameters": {
            "type": "object",
            "properties": {"radius": {"type": "integer"}, "color": {"type": "string"}},
            "required": ["radius", "color"],
        },
        "handler_code": (
            "def handle(radius: int, color: str) -> dict: return {'radius': radius, 'color': color}"
        ),
    }
    upd = gateway_client.put(f"/mcp/tools/{tool_name}", json=update_payload)
    assert upd.status_code == 200
    updated_tool = mcp.get_tool(tool_name)
    assert updated_tool is not None
    assert "color" in updated_tool.parameters["properties"]

    # Deregister tool
    del_resp = gateway_client.delete(f"/mcp/tools/{tool_name}")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "deregistered"
    assert mcp.get_tool(tool_name) is None
    assert gateway_client.delete(f"/mcp/tools/{tool_name}").status_code == 404
