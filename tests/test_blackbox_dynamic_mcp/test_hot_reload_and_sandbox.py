"""Blackbox tests verifying hot-reloading in-flight and AST sandbox rejection security."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from gateway_mcp.server import mcp


@pytest.mark.asyncio
async def test_blackbox_hot_reload_tool_logic_without_restart(client: TestClient):
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
        "handler_code": "def handle(dex_mod: int) -> dict: return {'total': 10 + dex_mod, 'version': 1}",
    }
    res1 = client.post("/mcp/tools/register", json=v1_payload)
    assert res1.status_code == 200

    tool_v1 = mcp.get_tool(tool_name)
    assert tool_v1 is not None
    out1 = await tool_v1.run({"dex_mod": 3})
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
        "handler_code": (
            "def handle(dex_mod: int, prof_bonus: int = 2) -> dict:\n"
            "    return {'total': 10 + dex_mod + prof_bonus, 'version': 2}\n"
        ),
    }
    res2 = client.put(f"/mcp/tools/{tool_name}", json=v2_payload)
    assert res2.status_code == 200
    assert res2.json()["status"] == "updated"

    # 3. Assert FastMCP immediately runs updated logic without server restart
    tool_v2 = mcp.get_tool(tool_name)
    assert "prof_bonus" in tool_v2.parameters["properties"]
    out2 = await tool_v2.run({"dex_mod": 3, "prof_bonus": 4})
    assert out2["total"] == 17
    assert out2["version"] == 2


def test_blackbox_sandbox_security_rejection(client: TestClient):
    """Verify security policies reject forbidden imports, calls, and attribute access."""
    forbidden_payloads = [
        ("os_import", "import os\ndef handle(): return os.getcwd()"),
        ("subprocess_import", "import subprocess\ndef handle(): return 1"),
        ("open_call", "def handle():\n    with open('/etc/passwd') as f: return f.read()"),
        ("eval_call", "def handle(): return eval('1 + 1')"),
        ("dunder_globals", "def handle(): return ().__class__.__bases__[0].__subclasses__()"),
    ]

    for name, code in forbidden_payloads:
        payload = {
            "name": name,
            "description": "Malicious code",
            "parameters": {"type": "object", "properties": {}},
            "handler_code": code,
        }
        res = client.post("/mcp/tools/register", json=payload)
        assert res.status_code == 400, f"Expected 400 Bad Request for {name}"
        assert "Sandbox policy violation" in res.json()["detail"]
        assert mcp.get_tool(name) is None, f"{name} must not be registered in FastMCP"


def test_blackbox_invalid_parameter_schema_rejection(client: TestClient):
    """Verify malformed parameter schemas are rejected cleanly."""
    # Top-level is not object
    bad_schema_1 = {
        "name": "bad_tool_1",
        "parameters": {"type": "array", "items": {"type": "string"}},
    }
    res1 = client.post("/mcp/tools/register", json=bad_schema_1)
    assert res1.status_code == 400
    assert "object" in res1.json()["detail"].lower()

    # Invalid JSON Schema
    bad_schema_2 = {
        "name": "bad_tool_2",
        "parameters": {"type": "object", "properties": "invalid_not_dict"},
    }
    res2 = client.post("/mcp/tools/register", json=bad_schema_2)
    assert res2.status_code == 400
