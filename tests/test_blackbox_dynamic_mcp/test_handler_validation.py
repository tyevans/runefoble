"""Blackbox tests for dynamic MCP handler validation.

A tool without a handler must never register.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.helpers.mcp_http import listed_tools_sync


def _handler_less_payload(name: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": name,
        "description": "Tool without logic",
        "parameters": {"type": "object", "properties": {}},
    }
    payload.update(overrides)
    return payload


@pytest.mark.parametrize(
    "overrides",
    [{"handler": None}, {"handler": {}}, {"handler": "   "}, {}],
    ids=["null", "empty", "blank", "missing"],
)
def test_blackbox_register_rejects_tool_without_handler(
    client: TestClient, overrides, mcp_endpoint: str
):
    """A definition with no handler is rejected with 422 and no tool is added."""
    name = "handler_less_probe"

    res = client.post("/mcp/tools/register", json=_handler_less_payload(name, **overrides))

    assert res.status_code == 422
    assert listed_tools_sync(mcp_endpoint).get(name) is None
    assert client.get(f"/mcp/tools/{name}").status_code == 404
