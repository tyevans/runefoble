"""Blackbox tests for declarative dynamic tool handlers (ADR-0020).

No caller text is compiled or run. A handler is data: a result template with
argument placeholders, arithmetic expressions, and dice expressions.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.helpers.mcp_http import call_tool_json, listed_tools_sync
from tests.helpers.ws_identity import SIGNING_ISSUER

PARAMS = {
    "type": "object",
    "properties": {
        "base": {"type": "integer"},
        "dist": {"type": "integer"},
        "who": {"type": "string"},
    },
    "required": ["base", "dist"],
}


def _register(client: TestClient, name: str, handler: object, parameters: dict | None = None):
    return client.post(
        "/mcp/tools/register",
        json={"name": name, "parameters": parameters or PARAMS, "handler": handler},
    )


def _execute(client: TestClient, name: str, arguments: dict):
    return client.post(f"/mcp/tools/{name}/execute", json={"arguments": arguments})


@pytest.mark.asyncio
async def test_template_expression_and_placeholder_results(client: TestClient, mcp_endpoint: str):
    handler = {
        "effective": {"$expr": "max(0, base - dist * 2)"},
        "echo_base": "${base}",
        "label": "${who} hits for ${base}",
        "nested": [{"$expr": "base // 3"}, "fixed", 7],
    }
    assert _register(client, "falloff", handler).status_code == 200

    res = _execute(client, "falloff", {"base": 25, "dist": 4, "who": "Ana"})

    assert res.status_code == 200
    assert res.json()["result"] == {
        "effective": 17,
        "echo_base": 25,
        "label": "Ana hits for 25",
        "nested": [8, "fixed", 7],
    }
    out = await call_tool_json(
        mcp_endpoint, "falloff", {"base": 30, "dist": 10}, SIGNING_ISSUER.mint("user-test")
    )
    assert out["effective"] == 10


def test_dice_expression_stays_in_range(client: TestClient):
    assert _register(client, "roller", {"total": {"$dice": "2d6+3"}}).status_code == 200
    for _ in range(30):
        total = _execute(client, "roller", {"base": 1, "dist": 1}).json()["result"]["total"]
        assert 5 <= total <= 15


@pytest.mark.parametrize(
    "handler",
    [
        {"x": {"$expr": "__import__('os').environ"}},
        {"x": {"$expr": "open('/etc/passwd')"}},
        {"x": {"$expr": "().__class__.__bases__"}},
        {"x": {"$expr": "base ** 99999999"}},
        {"x": {"$expr": "(lambda: 1)()"}},
        {"x": {"$expr": "ENV_SECRET"}},
        {"x": "${REDIS_URL}"},
        {"x": {"$call": "socket"}},
        {"x": {"$dice": "1000000d6"}},
        {"x": {"$dice": "not dice"}},
        {"x": {"$expr": "1 +"}},
        {"x": {"$expr": "base", "$dice": "1d6"}},
    ],
    ids=[
        "import",
        "open",
        "dunder",
        "pow",
        "lambda",
        "unknown_name",
        "unknown_placeholder",
        "unknown_directive",
        "huge_dice",
        "bad_dice",
        "syntax",
        "two_directives",
    ],
)
def test_registration_refuses_unsafe_or_invalid_handlers(
    client: TestClient, handler, mcp_endpoint: str
):
    res = _register(client, "probe_unsafe", handler)

    assert res.status_code == 400
    assert listed_tools_sync(mcp_endpoint).get("probe_unsafe") is None
    assert client.get("/mcp/tools/probe_unsafe").status_code == 404


def test_code_handlers_are_gone(client: TestClient, mcp_endpoint: str):
    payload = {
        "name": "legacy_code",
        "parameters": {"type": "object", "properties": {}},
        "handler_code": "def handle(): return 1",
    }
    res = client.post("/mcp/tools/register", json=payload)

    assert res.status_code == 422
    assert listed_tools_sync(mcp_endpoint).get("legacy_code") is None


def test_runtime_arithmetic_error_is_a_clean_400(client: TestClient):
    assert _register(client, "divider", {"x": {"$expr": "base / dist"}}).status_code == 200

    res = _execute(client, "divider", {"base": 1, "dist": 0})

    assert res.status_code == 400
    assert "division" in res.json()["detail"].lower()
