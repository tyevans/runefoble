"""Blackbox tests: dynamic tool routes take the author and caller from the verified bearer (TASK-0532).

Governed by ADR-0015 (c) and Hard Invariant 1. Identity never comes from a header or a
request body. The author recorded on a tool is the token subject.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from gateway_mcp.server import mcp
from runefoble_auth.spicedb import MockSpiceDBClient

from tests.helpers.mock_redis import MockAsyncRedis
from tests.test_blackbox_dynamic_mcp.conftest import caller_headers

TOOL = "arcane_pulse_probe"


def _payload(name: str = TOOL, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": name,
        "description": "Arcane pulse probe",
        "parameters": {"type": "object", "properties": {"charge": {"type": "integer"}}},
        "handler": {"pulse": {"$expr": "charge * 10"}},
    }
    payload.update(overrides)
    return payload


def test_every_tool_route_refuses_a_call_without_bearer(
    client: TestClient, anonymous_client: TestClient
):
    """Each route answers 401 before it looks at the tool, so no tool changes."""
    assert client.post("/mcp/tools/register", json=_payload()).status_code == 200
    assert mcp._tool_manager.get_tool(TOOL) is not None

    assert anonymous_client.get("/mcp/tools").status_code == 401
    assert anonymous_client.get("/mcp/tools/dynamic").status_code == 401
    assert anonymous_client.get(f"/mcp/tools/{TOOL}").status_code == 401
    assert (
        anonymous_client.post("/mcp/tools/register", json=_payload("anon_tool")).status_code == 401
    )
    assert anonymous_client.put(f"/mcp/tools/{TOOL}", json=_payload()).status_code == 401
    assert anonymous_client.delete(f"/mcp/tools/{TOOL}").status_code == 401
    assert (
        anonymous_client.post(f"/mcp/tools/{TOOL}/execute", json={"arguments": {"charge": 1}})
    ).status_code == 401

    assert mcp._tool_manager.get_tool("anon_tool") is None
    assert client.get(f"/mcp/tools/{TOOL}").status_code == 200


def test_x_user_id_header_is_not_an_identity(anonymous_client: TestClient):
    """A bare X-User-Id header no longer authenticates a register call."""
    res = anonymous_client.post(
        "/mcp/tools/register", json=_payload("header_probe"), headers={"X-User-Id": "alex"}
    )
    assert res.status_code == 401
    assert mcp._tool_manager.get_tool("header_probe") is None


def test_body_author_is_ignored_and_token_subject_is_recorded(client: TestClient):
    """The stored author equals the token subject, whatever the body says."""
    res = client.post(
        "/mcp/tools/register",
        json=_payload(author_id="mallory"),
        headers=caller_headers("alex"),
    )
    assert res.status_code == 200

    stored = client.get(f"/mcp/tools/{TOOL}", headers=caller_headers("alex")).json()["tool"]
    assert stored["author_id"] == "alex"


@pytest.mark.asyncio
async def test_author_relation_is_written_for_token_subject_only(
    client: TestClient, spicedb: MockSpiceDBClient
):
    """SpiceDB grants the author relation to the token subject, not to a body author."""
    client.post(
        "/mcp/tools/register",
        json=_payload(author_id="mallory"),
        headers=caller_headers("alex"),
    )
    assert await spicedb.check_permission("mcp_tool", TOOL, "manage", "user", "alex")
    assert not await spicedb.check_permission("mcp_tool", TOOL, "manage", "user", "mallory")


def test_execute_body_user_id_is_ignored(client: TestClient, mock_redis: MockAsyncRedis):
    """The execute body cannot name the caller. The event records the token subject."""
    client.post("/mcp/tools/register", json=_payload(), headers=caller_headers("alex"))

    res = client.post(
        f"/mcp/tools/{TOOL}/execute",
        json={"arguments": {"charge": 3}, "user_id": "mallory"},
        headers=caller_headers("alex"),
    )
    assert res.status_code == 200
    assert res.json()["result"] == {"pulse": 30}

    invoked = [
        json.loads(fields["payload"])
        for _, fields in mock_redis.streams.get("runefoble.events.system", [])
        if fields.get("event_type") == "runefoble.events.mcp_tools.dynamic_tool_invoked"
    ]
    assert invoked and invoked[-1]["user_id"] == "alex"
