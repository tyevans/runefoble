"""Blackbox tests (TASK-0847): deregistration revokes the author relation before it removes the tool.

A SpiceDB failure on the revoke keeps the tool registered and answers 503. A retry after the
outage removes the tool and the author relation. Every call goes through the public HTTP routes.
The only stub is the SpiceDB process boundary: `delete_relationship` raises the typed error.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.errors import AuthzUnavailableError
from runefoble_auth.mock import MockSpiceDBClient

from tests.test_blackbox_dynamic_mcp.conftest import caller_headers

AUTHOR = "author-revoke"
TOOL = "revocable_ward"
PAYLOAD = {
    "name": TOOL,
    "description": "Ward that the author can remove",
    "parameters": {"type": "object", "properties": {"strength": {"type": "integer"}}},
    "handler": {"ward": {"$expr": "strength * 2"}},
}


@pytest.mark.asyncio
async def test_revoke_outage_keeps_the_tool_and_answers_503(
    client: TestClient, spicedb: MockSpiceDBClient, monkeypatch: pytest.MonkeyPatch
):
    """A failed revoke returns 503 and leaves the tool listed and the author relation in place."""
    reg = client.post("/mcp/tools/register", json=PAYLOAD, headers=caller_headers(AUTHOR))
    assert reg.status_code == 200, reg.text

    async def unreachable(*_args, **_kwargs):
        raise AuthzUnavailableError("SpiceDB did not answer")

    monkeypatch.setattr(spicedb, "delete_relationship", unreachable)

    res = client.delete(f"/mcp/tools/{TOOL}", headers=caller_headers(AUTHOR))
    assert res.status_code == 503, res.text
    assert res.json()["detail"]["error"] == "authorization_unavailable"

    still_listed = client.get(f"/mcp/tools/{TOOL}", headers=caller_headers(AUTHOR))
    assert still_listed.status_code == 200
    assert await spicedb.check_permission("mcp_tool", TOOL, "manage", "user", AUTHOR)


@pytest.mark.asyncio
async def test_retry_after_outage_removes_tool_and_author_relation(
    client: TestClient, spicedb: MockSpiceDBClient, monkeypatch: pytest.MonkeyPatch
):
    """After the outage ends, a retry returns 200, the tool is gone, and the author relation is absent."""
    client.post("/mcp/tools/register", json=PAYLOAD, headers=caller_headers(AUTHOR))

    async def unreachable(*_args, **_kwargs):
        raise AuthzUnavailableError("SpiceDB did not answer")

    monkeypatch.setattr(spicedb, "delete_relationship", unreachable)
    failed = client.delete(f"/mcp/tools/{TOOL}", headers=caller_headers(AUTHOR))
    assert failed.status_code == 503

    monkeypatch.undo()
    retry = client.delete(f"/mcp/tools/{TOOL}", headers=caller_headers(AUTHOR))
    assert retry.status_code == 200, retry.text
    assert retry.json()["status"] == "deregistered"

    assert client.get(f"/mcp/tools/{TOOL}", headers=caller_headers(AUTHOR)).status_code == 404
    assert not await spicedb.check_permission("mcp_tool", TOOL, "manage", "user", AUTHOR)
