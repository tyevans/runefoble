"""Two gateway apps built from two containers keep separate dynamic tool registries (TASK-0746).

Each app is driven only through its public tool admin routes. No test reads a registry
object or a module global.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from gateway_mcp.container import GatewayMcpContainer
from runefoble_auth.mock import MockSpiceDBClient

from tests.helpers.mcp_http import mcp_http_app
from tests.helpers.ws_identity import SIGNING_ISSUER

TOOL_BODY = {
    "name": "isolated_falloff",
    "description": "Falloff in one app only",
    "parameters": {
        "type": "object",
        "properties": {"distance": {"type": "integer", "description": "Tiles"}},
        "required": ["distance"],
    },
    "handler": {"damage": {"$expr": "max(0, 10 - distance)"}},
    "metadata": {"version": "1.0.0", "author": "modder-1"},
}


def _app_client(container: GatewayMcpContainer) -> TestClient:
    headers = {"Authorization": f"Bearer {SIGNING_ISSUER.mint('user-test')}"}
    return TestClient(mcp_http_app(container), headers=headers)


def test_blackbox_two_gateway_apps_keep_separate_registries(spicedb: MockSpiceDBClient):
    first_app = _app_client(GatewayMcpContainer.default())
    second_app = _app_client(GatewayMcpContainer.default())

    registered = first_app.post("/mcp/tools/register", json=TOOL_BODY)
    assert registered.status_code == 200, registered.text

    first_listing = first_app.get("/mcp/tools/dynamic").json()
    second_listing = second_app.get("/mcp/tools/dynamic").json()
    assert [t["name"] for t in first_listing["tools"]] == ["isolated_falloff"]
    assert second_listing["tools"] == []
    assert second_app.get("/mcp/tools/isolated_falloff").status_code == 404
