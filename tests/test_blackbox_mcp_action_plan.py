"""Blackbox TDD tests for TASK-0747: the MCP action plan runner validates, maps, and proposes steps.

The Watcher and game_session run as real HTTP servers on loopback ports. Setup runs through
public routes with a signed bearer. Assertions read the MCP tool output and the public
pending-actions route of The Watcher. A failed step must leave no request in The Watcher.
"""

import json
from collections.abc import Iterator
from typing import Any

import httpx
import pytest
from mcp.types import CallToolResult
from the_watcher.main import app as watcher_app

from tests.helpers.campaign_setup import create_owned_campaign
from tests.helpers.live_services import serve
from tests.helpers.mcp_http import call_tool_over_http, serve_mcp
from tests.helpers.ws_identity import SIGNING_ISSUER, bearer

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer", "board_campaign")

_MCP: dict[str, str] = {}


@pytest.fixture(scope="module")
def upstreams() -> Iterator[dict[str, str]]:
    """Run The Watcher and game_session as real HTTP servers."""
    from game_session.main import app as session_app

    with serve(watcher_app) as watcher_url, serve(session_app) as session_url:
        yield {"watcher": watcher_url, "session": session_url}


@pytest.fixture
def services(upstreams: dict[str, str], monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Point the gateway at the live upstream services for one test."""
    monkeypatch.setenv("RUNEFOBLE_WATCHER_URL", upstreams["watcher"])
    monkeypatch.setenv("RUNEFOBLE_GAME_SESSION_URL", upstreams["session"])
    return upstreams


@pytest.fixture(scope="module", autouse=True)
def mcp_endpoint() -> Iterator[None]:
    """Serve the gateway MCP server over HTTP so each call carries the caller bearer."""
    with serve_mcp() as endpoint:
        _MCP["url"] = endpoint
        yield
    _MCP.clear()


def _create_session(session_url: str, title: str) -> tuple[str, str]:
    """Create a game session through game_session and return (session_id, campaign_id)."""
    with httpx.Client(base_url=session_url, headers=bearer("user-test")) as http:
        owned_campaign_id = create_owned_campaign(http)
        created = http.post(
            f"/api/v1/campaigns/{owned_campaign_id}/sessions",
            json={"title": title},
        )
        assert created.status_code == 201, created.text
        session_id = str(created.json()["id"])
        campaign_id = http.get(f"/api/v1/sessions/{session_id}").json()["campaign_id"]
    return session_id, str(campaign_id)


async def _call_plan(session_id: str, campaign_id: str, actions: list[dict[str, Any]]):
    """Run execute_agent_action_plan over MCP as the `user-test` caller."""
    result = await call_tool_over_http(
        _MCP["url"],
        "execute_agent_action_plan",
        {"session_id": session_id, "campaign_id": campaign_id, "actions": actions},
        SIGNING_ISSUER.mint("user-test"),
    )
    assert not result.isError, _text(result)
    data = json.loads(_text(result))
    assert isinstance(data, dict)
    return data


def _text(result: CallToolResult) -> str:
    assert result.content, "Tool result must contain content"
    return str(result.content[0].text)


def _pending_actions(watcher_url: str, session_id: str, campaign_id: str) -> list[dict[str, Any]]:
    """Read the pending actions that The Watcher holds for the session, as the DM."""
    with httpx.Client(base_url=watcher_url, headers=bearer("user-test")) as http:
        response = http.get(
            "/api/v1/watcher/actions/pending",
            params={"session_id": session_id, "campaign_id": campaign_id},
        )
        assert response.status_code == 200, response.text
        return list(response.json())


def _roll(actor: str, notation: str = "1d20") -> dict[str, Any]:
    return {
        "tool": "roll_dice",
        "actor_name": actor,
        "parameters": {"notation": notation, "reason": "Check"},
    }


@pytest.mark.asyncio
async def test_blackbox_plan_with_two_valid_steps_proposes_both_in_order(services):
    """Verify each valid step is proposed in order, and the Watcher holds both actions."""
    session_id, campaign_id = _create_session(services["session"], "Goblin Warren")
    plan = [
        {
            "tool": "roll_dice",
            "actor_name": "Goblin Archer",
            "description": "Slip behind the barrels",
            "parameters": {"notation": "1d20+3", "reason": "Stealth"},
        },
        _roll("Goblin Archer", "1d8"),
    ]

    result = await _call_plan(session_id, campaign_id, plan)

    assert result["success"] is True
    assert result["completed_steps"] == 2
    assert [step["step"] for step in result["steps"]] == [1, 2]
    assert all(step["status"] == "success" for step in result["steps"])
    first = result["steps"][0]["output"]
    assert first["session_id"] == session_id
    assert first["campaign_id"] == campaign_id
    assert first["action_type"] == "roll_dice"
    assert first["actor_name"] == "Goblin Archer"
    assert first["description"] == "Slip behind the barrels"
    held = _pending_actions(services["watcher"], session_id, campaign_id)
    assert [action["description"] for action in held] == ["Slip behind the barrels", "roll_dice"]


@pytest.mark.asyncio
async def test_blackbox_plan_unknown_tool_stops_at_its_step_before_watcher(services):
    """Verify an unknown tool fails its own step. Later steps and the Watcher get no request."""
    session_id, campaign_id = _create_session(services["session"], "Drowned Vault")
    plan = [
        _roll("Kyra"),
        {
            "tool": "nonexistent_secret_spell_destroy_everything",
            "actor_name": "Valeros",
            "parameters": {"target": "all"},
        },
        _roll("Seoni"),
    ]

    result = await _call_plan(session_id, campaign_id, plan)

    assert result["status"] == "error"
    assert result["success"] is False
    assert result["failed_step"] == 2
    assert result["completed_steps"] == 1
    assert result["total_steps"] == 3
    assert [step["step"] for step in result["steps"]] == [1, 2]
    assert result["steps"][1]["status"] == "error"
    assert "nonexistent_secret_spell_destroy_everything" in result["error"]
    held = _pending_actions(services["watcher"], session_id, campaign_id)
    assert [action["actor_name"] for action in held] == ["Kyra"]


@pytest.mark.asyncio
async def test_blackbox_plan_missing_actor_name_fails_before_any_proposal(services):
    """Verify a step without actor_name fails before the Watcher gets any request."""
    session_id, campaign_id = _create_session(services["session"], "Silent Hall")
    plan = [
        {"tool": "roll_dice", "parameters": {"notation": "1d20", "reason": "Check"}},
        _roll("Kyra"),
    ]

    result = await _call_plan(session_id, campaign_id, plan)

    assert result["status"] == "error"
    assert result["failed_step"] == 1
    assert result["completed_steps"] == 0
    assert "actor_name" in result["error"]
    assert _pending_actions(services["watcher"], session_id, campaign_id) == []


@pytest.mark.asyncio
async def test_blackbox_plan_accepts_only_the_tool_key_for_the_tool_name(services):
    """Verify a step that names its tool under another key fails. One key per field."""
    session_id, campaign_id = _create_session(services["session"], "Ash Gate")
    plan = [{"name": "roll_dice", "actor_name": "Kyra", "parameters": {"notation": "1d20"}}]

    result = await _call_plan(session_id, campaign_id, plan)

    assert result["failed_step"] == 1
    assert result["completed_steps"] == 0
    assert "'tool'" in result["error"]
    assert _pending_actions(services["watcher"], session_id, campaign_id) == []
