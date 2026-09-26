"""Blackbox TDD integration test suite for Universal VTT Importer & Dynamic FastMCP Registry.

Governed by:
- TASK-0057
- ADR-0007: Real-Time Voice and Board Synchronization
- ADR-0008: FastMCP Gateway Architecture
- ADR-0010: Silo S3 Media Storage Pipeline
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

import base64
import json
from uuid import uuid4

import pytest
from board_state.main import app as board_app
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from gateway_mcp.server import dynamic_registry, mcp
from runefoble_platform.storage import get_storage_service

from tests.helpers.silo_fixtures import PNG_SAMPLE_BYTES


@pytest.fixture
def board_client() -> TestClient:
    return TestClient(board_app)


@pytest.fixture
def gateway_client() -> TestClient:
    return TestClient(gateway_app)


@pytest.fixture(autouse=True)
def clean_environment():
    """Ensure clean storage and dynamic registry for each test."""
    storage = get_storage_service()
    storage.clear()
    for tool_def in list(dynamic_registry.list_tools()):
        dynamic_registry.deregister_tool(tool_def.name)
    yield
    for tool_def in list(dynamic_registry.list_tools()):
        dynamic_registry.deregister_tool(tool_def.name)
    storage.clear()


def build_sample_dd2vtt_dict(
    cols: int = 16,
    rows: int = 12,
    pixels_per_grid: int = 70,
    include_image: bool = True,
) -> dict:
    """Build a canonical Universal VTT (.dd2vtt) dictionary."""
    b64_img = base64.b64encode(PNG_SAMPLE_BYTES).decode("utf-8") if include_image else ""
    return {
        "format": 0.2,
        "resolution": {
            "map_origin": {"x": 0, "y": 0},
            "map_size": {"x": cols, "y": rows},
            "pixels_per_grid": pixels_per_grid,
        },
        "line_of_sight": [
            [{"x": 1.0, "y": 1.0}, {"x": 6.0, "y": 1.0}],
            [{"x": 6.0, "y": 1.0}, {"x": 6.0, "y": 5.0}],
            [{"x": 6.0, "y": 5.0}, {"x": 1.0, "y": 5.0}],
        ],
        "portals": [
            {
                "position": {"x": 3.5, "y": 1.0},
                "bounds": [{"x": 3.0, "y": 1.0}, {"x": 4.0, "y": 1.0}],
                "rotation": 0.0,
                "closed": True,
                "freestanding": False,
            }
        ],
        "lights": [
            {
                "position": {"x": 4.0, "y": 3.0},
                "range": 5.5,
                "intensity": 0.85,
                "color": "ffffc0a0",
                "shadows": True,
            }
        ],
        "image": b64_img,
    }


def test_blackbox_uvtt_multipart_file_upload(board_client: TestClient):
    """Verify importing a .dd2vtt file via multipart/form-data frontdoor."""
    board_id = f"camp-uvtt-{uuid4().hex[:8]}"
    uvtt_data = build_sample_dd2vtt_dict(cols=18, rows=14, pixels_per_grid=100)
    file_bytes = json.dumps(uvtt_data).encode("utf-8")

    # Frontdoor invocation: POST /api/v1/board/{id}/import/uvtt
    response = board_client.post(
        f"/api/v1/board/{board_id}/import/uvtt",
        files={"file": ("crypt_dungeon.dd2vtt", file_bytes, "application/json")},
    )
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["status"] == "imported"
    assert data["cols"] == 18
    assert data["rows"] == 14
    assert data["pixels_per_grid"] == 100
    assert len(data["wall_segments"]) == 3
    assert data["wall_segments"][0]["x1"] == 1.0
    assert data["wall_segments"][0]["y1"] == 1.0
    assert data["wall_segments"][0]["x2"] == 6.0
    assert data["wall_segments"][0]["y2"] == 1.0

    # Door portals & lights extraction
    assert len(data["portals"]) == 1
    assert data["portals"][0]["position"] == {"x": 3.5, "y": 1.0}
    assert data["portals"][0]["closed"] is True
    assert len(data["lights"]) == 1
    assert data["lights"][0]["range"] == 5.5

    # Background texture stored into Silo S3
    assert data["background_image_url"] is not None
    assert data["background_asset_id"] is not None
    storage = get_storage_service()
    asset = storage.get_asset_by_id(data["background_asset_id"])
    assert asset["content_type"] == "image/png"
    assert asset["byte_size"] == len(PNG_SAMPLE_BYTES)

    # Observable public projection check via GET /api/v1/boards/{board_id}
    get_res = board_client.get(f"/api/v1/boards/{board_id}")
    assert get_res.status_code == 200
    board_state = get_res.json()
    assert board_state["cols"] == 18
    assert board_state["rows"] == 14
    assert len(board_state["wall_segments"]) == 3
    assert board_state["background_image_url"] == data["background_image_url"]

    # Wall obstacle tokens placed within board boundaries
    obstacle_tokens = [
        t for t in board_state["tokens"].values() if t.get("token_type") == "obstacle"
    ]
    assert len(obstacle_tokens) >= 1
    coords = {(t["x"], t["y"]) for t in obstacle_tokens}
    assert (1, 1) in coords or (6, 1) in coords


def test_blackbox_uvtt_json_direct_payload(board_client: TestClient):
    """Verify importing a .dd2vtt map via raw JSON payload frontdoor."""
    board_id = f"board-{uuid4().hex[:8]}"
    uvtt_data = build_sample_dd2vtt_dict(cols=24, rows=18, pixels_per_grid=70)

    # Plural route alias frontdoor: POST /api/v1/boards/{id}/import/uvtt
    response = board_client.post(
        f"/api/v1/boards/{board_id}/import/uvtt",
        json=uvtt_data,
    )
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["status"] == "imported"
    assert data["cols"] == 24
    assert data["rows"] == 18
    assert len(data["wall_segments"]) == 3

    # Verify query projection
    get_res = board_client.get(f"/api/v1/boards/{board_id}")
    assert get_res.status_code == 200
    assert get_res.json()["cols"] == 24


def test_blackbox_uvtt_invalid_payload_error(board_client: TestClient):
    """Verify error handling on malformed UVTT data."""
    board_id = f"board-{uuid4().hex[:8]}"
    response = board_client.post(
        f"/api/v1/board/{board_id}/import/uvtt",
        content=b"not-valid-json-file-content",
        headers={"Content-Type": "application/octet-stream"},
    )
    assert response.status_code == 400
    assert "Invalid Universal VTT format" in response.json()["detail"]


@pytest.mark.asyncio
async def test_blackbox_dynamic_mcp_tool_registration_and_execution(
    gateway_client: TestClient,
):
    """Verify registering a dynamic tool via administrative frontdoor and invoking it in FastMCP."""
    tool_name = "calculate_spell_falloff"

    # 1. Assert tool not registered initially in FastMCP
    assert mcp.get_tool(tool_name) is None

    # 2. Register dynamic tool definition via administrative HTTP frontdoor
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

    # 3. Assert tool is immediately visible in FastMCP discovery WITHOUT gateway restart
    registered_tool = mcp.get_tool(tool_name)
    assert registered_tool is not None, "Tool must be discovered immediately in FastMCP"
    assert "base_damage" in registered_tool.parameters["properties"]
    assert "distance" in registered_tool.parameters["properties"]

    # 4. Invoke the dynamic tool through public FastMCP tool interface
    mcp_result = await registered_tool.run({"base_damage": 25, "distance": 4})
    assert mcp_result["effective_damage"] == 17
    assert mcp_result["reduced_by"] == 8

    # 5. Invoke through administrative HTTP execution frontdoor
    exec_resp = gateway_client.post(
        f"/mcp/tools/{tool_name}/execute",
        json={"arguments": {"base_damage": 30, "distance": 10}},
    )
    assert exec_resp.status_code == 200
    res_data = exec_resp.json()
    assert res_data["status"] == "success"
    assert res_data["result"]["effective_damage"] == 10
    assert res_data["result"]["reduced_by"] == 20

    # 6. Listing dynamic tools endpoint
    list_resp = gateway_client.get("/mcp/tools")
    assert list_resp.status_code == 200
    tool_names = [t["name"] for t in list_resp.json()["tools"]]
    assert tool_name in tool_names


def test_blackbox_dynamic_mcp_sandbox_rejection_security(gateway_client: TestClient):
    """Verify sandbox policies reject dangerous system calls or restricted imports."""
    unsafe_payloads = [
        # Disallowed import: os
        {
            "name": "malicious_tool_os",
            "parameters": {"type": "object", "properties": {}},
            "handler_code": "import os\ndef handle(): return os.getcwd()",
        },
        # Disallowed import: subprocess
        {
            "name": "malicious_tool_subprocess",
            "parameters": {"type": "object", "properties": {}},
            "handler_code": "import subprocess\ndef handle(): return subprocess.run('ls')",
        },
        # Disallowed call: open
        {
            "name": "malicious_tool_open",
            "parameters": {"type": "object", "properties": {}},
            "handler_code": "def handle():\n    with open('/etc/passwd') as f: return f.read()",
        },
        # Disallowed dunder attribute access: __globals__
        {
            "name": "malicious_tool_dunder",
            "parameters": {"type": "object", "properties": {}},
            "handler_code": "def handle(): return ().__class__.__bases__[0].__subclasses__()",
        },
    ]

    for payload in unsafe_payloads:
        resp = gateway_client.post("/mcp/tools", json=payload)
        assert resp.status_code == 400, f"Expected rejection for {payload['name']}"
        assert "Sandbox policy violation" in resp.json()["detail"]
        assert mcp.get_tool(payload["name"]) is None


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

    # 1. Register tool
    reg = gateway_client.post("/mcp/tools", json=initial_payload)
    assert reg.status_code == 200
    assert mcp.get_tool(tool_name) is not None

    # 2. Update tool with new description and parameters
    update_payload = {
        "name": tool_name,
        "description": "Launch enhanced illumination flare with color",
        "parameters": {
            "type": "object",
            "properties": {
                "radius": {"type": "integer"},
                "color": {"type": "string"},
            },
            "required": ["radius", "color"],
        },
        "handler_code": "def handle(radius: int, color: str) -> dict: return {'radius': radius, 'color': color}",
    }
    upd = gateway_client.put(f"/mcp/tools/{tool_name}", json=update_payload)
    assert upd.status_code == 200
    updated_tool = mcp.get_tool(tool_name)
    assert updated_tool is not None
    assert "color" in updated_tool.parameters["properties"]

    # 3. Deregister tool
    del_resp = gateway_client.delete(f"/mcp/tools/{tool_name}")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "deregistered"

    # 4. Assert tool is removed from FastMCP discovery
    assert mcp.get_tool(tool_name) is None

    # 5. Deregistering nonexistent tool returns 404
    assert gateway_client.delete(f"/mcp/tools/{tool_name}").status_code == 404
