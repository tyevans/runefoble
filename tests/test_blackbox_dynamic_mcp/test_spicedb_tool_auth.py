"""Blackbox tests verifying SpiceDB Zanzibar fine-grained authorization on dynamic MCP tools."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.mock_spicedb import MockSpiceDBClient


@pytest.mark.asyncio
async def test_blackbox_spicedb_author_manage_and_unauthorized_rejection(
    client: TestClient, mock_spicedb: MockSpiceDBClient
):
    """Verify that only authorized authors can modify or deregister a dynamic tool."""
    tool_name = "secret_arcane_pulse"
    payload = {
        "name": tool_name,
        "description": "Arcane pulse emitter",
        "parameters": {"type": "object", "properties": {"charge": {"type": "integer"}}},
        "handler_code": "def handle(charge: int = 1): return {'pulse_strength': charge * 10}",
    }

    # 1. Author 'alex' registers the tool
    res = client.post("/mcp/tools/register", json=payload, headers={"X-User-Id": "alex"})
    assert res.status_code == 200

    # 2. Unauthorized user 'bob' tries to update the tool -> 403 Forbidden
    updated_payload = dict(payload, description="Hacked pulse emitter")
    unauth_update = client.put(
        f"/mcp/tools/{tool_name}", json=updated_payload, headers={"X-User-Id": "bob"}
    )
    assert unauth_update.status_code == 403
    assert "Permission denied" in unauth_update.json()["detail"]

    # 3. Unauthorized user 'bob' tries to delete the tool -> 403 Forbidden
    unauth_delete = client.delete(f"/mcp/tools/{tool_name}", headers={"X-User-Id": "bob"})
    assert unauth_delete.status_code == 403
    assert "Permission denied" in unauth_delete.json()["detail"]

    # 4. Author 'alex' can update and delete the tool successfully
    auth_update = client.put(
        f"/mcp/tools/{tool_name}", json=updated_payload, headers={"X-User-Id": "alex"}
    )
    assert auth_update.status_code == 200
    assert auth_update.json()["status"] == "updated"

    auth_delete = client.delete(f"/mcp/tools/{tool_name}", headers={"X-User-Id": "alex"})
    assert auth_delete.status_code == 200
    assert auth_delete.json()["status"] == "deregistered"


@pytest.mark.asyncio
async def test_blackbox_spicedb_campaign_scoped_permissions(
    client: TestClient, mock_spicedb: MockSpiceDBClient
):
    """Verify campaign DM and player permissions granted via Zanzibar schema traversal."""
    campaign_id = "camp-valeros"
    tool_name = "tactical_strike"
    payload = {
        "name": tool_name,
        "description": "Tactical combat strike",
        "campaign_id": campaign_id,
        "author_id": "author-dev",
        "parameters": {"type": "object", "properties": {"power": {"type": "integer"}}},
        "handler_code": "def handle(power: int = 5): return {'damage': power * 2}",
    }

    # Setup campaign relationships in SpiceDB
    await mock_spicedb.write_relationship(
        "campaign", campaign_id, "dungeon_master", "user", "dm-evelyn"
    )
    await mock_spicedb.write_relationship(
        "campaign", campaign_id, "player", "user", "player-valeros"
    )
    await mock_spicedb.write_relationship(
        "campaign", campaign_id, "spectator", "user", "spectator-sam"
    )

    # Author registers tool linked to campaign
    reg = client.post("/mcp/tools/register", json=payload, headers={"X-User-Id": "author-dev"})
    assert reg.status_code == 200

    # 1. Player can execute tool (granted via campaign->play)
    play_res = client.post(
        f"/mcp/tools/{tool_name}/execute",
        json={"arguments": {"power": 6}},
        headers={"X-User-Id": "player-valeros"},
    )
    assert play_res.status_code == 200
    assert play_res.json()["result"]["damage"] == 12

    # 2. Spectator cannot execute tool (spectators cannot play)
    spec_exec = client.post(
        f"/mcp/tools/{tool_name}/execute",
        json={"arguments": {"power": 6}},
        headers={"X-User-Id": "spectator-sam"},
    )
    assert spec_exec.status_code == 403

    # 3. Player cannot delete tool (players cannot manage)
    play_del = client.delete(f"/mcp/tools/{tool_name}", headers={"X-User-Id": "player-valeros"})
    assert play_del.status_code == 403

    # 4. DM can manage and delete tool (granted via campaign->run_session)
    dm_del = client.delete(f"/mcp/tools/{tool_name}", headers={"X-User-Id": "dm-evelyn"})
    assert dm_del.status_code == 200
