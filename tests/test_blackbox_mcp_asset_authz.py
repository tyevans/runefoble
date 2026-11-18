"""Blackbox tests for MCP tool and gateway asset authorization (TASK-0545).

Governed by ADR-0001 (schema permissions only) and ADR-0015 (verified bearer identity).
Every call goes through a public frontdoor: the gateway HTTP routes, the MCP streamable
HTTP transport, and the live character_sheet and game_session upstreams. Setup uses the
public campaign, invite, character, register, and upload routes. The only double is a
SpiceDB client that fails, which stands in for an unreachable external service.
"""

from __future__ import annotations

import asyncio
import base64
from collections.abc import Iterator
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app
from gateway_mcp.dynamic import dynamic_registry
from gateway_mcp.dynamic.auth import set_spicedb_client
from gateway_mcp.server import mcp
from runefoble_auth.errors import AuthzError
from runefoble_auth.spicedb import MockSpiceDBClient

from tests.helpers.mcp_http import call_tool_over_http, serve_mcp
from tests.helpers.silo_fixtures import PNG_SAMPLE_BYTES
from tests.helpers.ws_identity import SIGNING_ISSUER

TOOL_NAME = "authz_probe_tool"
DEFINITION = {
    "name": TOOL_NAME,
    "description": "Doubles a number.",
    "parameters": {"type": "object", "properties": {"n": {"type": "integer"}}, "required": ["n"]},
    "handler": {"doubled": {"$expr": "n * 2"}},
}


@pytest.fixture(scope="module")
def mcp_endpoint() -> Iterator[str]:
    """Serve the MCP gateway over HTTP. The endpoint trusts the shared signing issuer."""
    with serve_mcp(mcp) as endpoint:
        yield endpoint


@pytest.fixture
def gateway(character_sheet_upstream, game_session_upstream, asset_forge_upstream, silo_double):
    """Enter the gateway lifespan after the upstreams serve."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def registry(mcp_endpoint: str) -> Iterator[httpx.Client]:
    """Call the tool admin routes on the MCP process, where the registry lives."""
    with httpx.Client(base_url=mcp_endpoint.removesuffix("/mcp")) as client:
        yield client
    if dynamic_registry.get_tool(TOOL_NAME):
        dynamic_registry.deregister_tool(TOOL_NAME)


def auth(sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


def call(endpoint: str, sub: str, tool: str, arguments: dict[str, Any]):
    return asyncio.run(call_tool_over_http(endpoint, tool, arguments, SIGNING_ISSUER.mint(sub)))


def result_text(result) -> str:
    return str(result.content[0].text) if result.content else ""


def make_party(gateway: TestClient, dm: str, player: str) -> str:
    """Create a campaign as the DM and let the player join through an invite."""
    campaign_id = gateway.post(
        "/api/v1/campaigns", json={"title": "Authz Party", "setting": "Test"}, headers=auth(dm)
    ).json()["id"]
    invite = gateway.post(
        f"/api/v1/campaigns/{campaign_id}/invites", json={"role": "player"}, headers=auth(dm)
    )
    joined = gateway.post(
        "/api/v1/campaigns/join",
        json={"invite_token": invite.json()["token"]},
        headers=auth(player),
    )
    assert joined.status_code == 200, joined.text
    return str(campaign_id)


def make_character(gateway: TestClient, owner: str, campaign_id: str) -> str:
    char_id = gateway.post(
        "/api/v1/characters",
        json={"name": "Valeros", "characterClass": "Fighter", "maxHp": 40},
        headers=auth(owner),
    ).json()["id"]
    res = gateway.patch(
        f"/api/v1/characters/{char_id}/campaign",
        json={"campaignId": campaign_id},
        headers=auth(owner),
    )
    assert res.status_code == 200, res.text
    return str(char_id)


# --- Registry routes ---


def test_anonymous_register_is_refused(registry):
    assert registry.post("/mcp/tools/register", json=DEFINITION).status_code == 401


def test_only_the_author_may_delete_a_tool(registry):
    registered = registry.post("/mcp/tools/register", json=DEFINITION, headers=auth("alice"))
    assert registered.status_code == 200, registered.text
    assert registry.delete(f"/mcp/tools/{TOOL_NAME}", headers=auth("mallory")).status_code == 403
    assert registry.delete(f"/mcp/tools/{TOOL_NAME}", headers=auth("alice")).status_code == 200


def test_body_author_does_not_choose_the_author(registry):
    body = {**DEFINITION, "author_id": "mallory"}
    assert registry.post("/mcp/tools/register", json=body, headers=auth("alice")).status_code == 200
    tool = registry.get(f"/mcp/tools/{TOOL_NAME}", headers=auth("alice")).json()["tool"]
    assert tool["author_id"] == "alice"


def test_register_fails_closed_when_authorization_is_down(registry):
    class DownSpiceDB(MockSpiceDBClient):
        async def write_relationship(self, *args, **kwargs):
            raise AuthzError("SpiceDB unreachable")

    set_spicedb_client(DownSpiceDB())
    response = registry.post("/mcp/tools/register", json=DEFINITION, headers=auth("alice"))
    assert response.status_code == 503, response.text
    assert dynamic_registry.get_tool(TOOL_NAME) is None


def test_execute_needs_the_execute_permission_over_http_and_mcp(registry, mcp_endpoint):
    registry.post("/mcp/tools/register", json=DEFINITION, headers=auth("alice"))
    denied = registry.post(
        f"/mcp/tools/{TOOL_NAME}/execute", json={"arguments": {"n": 2}}, headers=auth("mallory")
    )
    assert denied.status_code == 403
    stranger = call(mcp_endpoint, "mallory", TOOL_NAME, {"n": 2})
    assert stranger.isError is True
    assert "Permission denied" in result_text(stranger)
    author = call(mcp_endpoint, "alice", TOOL_NAME, {"n": 2})
    assert author.isError is False
    assert "4" in result_text(author)


# --- Static MCP tools ---


def test_player_cannot_apply_a_penalty_but_the_dm_can(gateway, mcp_endpoint):
    campaign_id = make_party(gateway, "dm_merlin", "player_alice")
    char_id = make_character(gateway, "player_alice", campaign_id)
    args = {"character_id": char_id, "penalty_type": "drunk", "explanation": "Missed game night"}

    player = call(mcp_endpoint, "player_alice", "apply_absentee_penalty", args)
    assert player.isError is True
    assert "Permission denied" in result_text(player)
    sheet = gateway.get(f"/api/v1/characters/{char_id}", headers=auth("player_alice")).json()
    assert not sheet["penalties"]

    dm = call(mcp_endpoint, "dm_merlin", "apply_absentee_penalty", args)
    assert dm.isError is False, result_text(dm)
    sheet = gateway.get(f"/api/v1/characters/{char_id}", headers=auth("player_alice")).json()
    assert sheet["penalties"]


def test_player_cannot_change_hit_points_or_conditions(gateway, mcp_endpoint):
    campaign_id = make_party(gateway, "dm_merlin", "player_alice")
    char_id = make_character(gateway, "player_alice", campaign_id)
    hp = call(
        mcp_endpoint, "player_alice", "modify_character_hp", {"character_id": char_id, "delta": 20}
    )
    cond = call(
        mcp_endpoint,
        "player_alice",
        "add_condition",
        {"character_id": char_id, "condition": "prone"},
    )
    assert "Permission denied" in result_text(hp)
    assert "Permission denied" in result_text(cond)
    dm = call(
        mcp_endpoint, "dm_merlin", "modify_character_hp", {"character_id": char_id, "delta": -5}
    )
    assert dm.isError is False, result_text(dm)


def test_stranger_cannot_cast_move_or_start_an_encounter(gateway, mcp_endpoint):
    campaign_id = make_party(gateway, "dm_merlin", "player_alice")
    char_id = make_character(gateway, "player_alice", campaign_id)
    calls = [
        ("cast_spell", {"character_id": char_id, "spell_name": "Light", "spell_level": 0}),
        ("move_board_token", {"session_id": "s1", "token_id": "t1", "to_x": 1, "to_y": 1}),
        ("create_encounter", {"session_id": "s1"}),
    ]
    for tool, args in calls:
        result = call(mcp_endpoint, "mallory", tool, args)
        assert result.isError is True, tool
        assert "Permission denied" in result_text(result), tool


def test_plan_stops_at_the_first_step_the_caller_may_not_run(gateway, mcp_endpoint):
    campaign_id = make_party(gateway, "dm_merlin", "player_alice")
    char_id = make_character(gateway, "player_alice", campaign_id)
    plan = {
        "session_id": "s1",
        "campaign_id": campaign_id,
        "actions": [
            {
                "tool": "modify_character_hp",
                "actor_name": "Alice",
                "parameters": {"character_id": char_id, "delta": 10},
            }
        ],
    }
    result = call(mcp_endpoint, "player_alice", "execute_agent_action_plan", plan)
    payload = result_text(result)
    assert "Permission denied" in payload
    assert '"failed_step": 1' in payload


# --- Gateway assets ---


def upload(gateway: TestClient, sub: str, campaign_id: str | None = None):
    body: dict[str, Any] = {
        "filename": "map.png",
        "content_type": "image/png",
        "data_base64": base64.b64encode(PNG_SAMPLE_BYTES).decode(),
        "asset_type": "battlemap",
    }
    if campaign_id:
        body["campaign_id"] = campaign_id
    return gateway.post("/api/v1/assets/upload", json=body, headers=auth(sub))


def test_anonymous_asset_delete_is_refused(gateway):
    asset_id = upload(gateway, "alice").json()["asset_id"]
    assert gateway.delete(f"/api/v1/assets/{asset_id}").status_code == 401


def test_only_the_creator_may_delete_an_asset(gateway):
    asset_id = upload(gateway, "alice").json()["asset_id"]
    assert gateway.delete(f"/api/v1/assets/{asset_id}", headers=auth("mallory")).status_code == 403
    assert gateway.get(f"/api/v1/assets/{asset_id}", headers=auth("alice")).status_code == 200
    assert gateway.delete(f"/api/v1/assets/{asset_id}", headers=auth("alice")).status_code == 200


def test_campaign_dm_may_delete_a_campaign_asset(gateway):
    campaign_id = make_party(gateway, "dm_merlin", "player_alice")
    asset_id = upload(gateway, "player_alice", campaign_id).json()["asset_id"]
    assert (
        gateway.delete(f"/api/v1/assets/{asset_id}", headers=auth("dm_merlin")).status_code == 200
    )


def test_asset_cannot_join_a_campaign_the_uploader_cannot_play_in(gateway):
    campaign_id = make_party(gateway, "dm_merlin", "player_alice")
    assert upload(gateway, "mallory", campaign_id).status_code == 403
