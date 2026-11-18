"""Blackbox TDD tests for TASK-0605: MCP narration, action plans, and session resources call services.

Upstream services run as real HTTP servers on loopback ports: the_watcher, game_session,
board_state, and rules_compendium. The inference worker is a fake HTTP server, because it is
an external process boundary. Setup runs through public routes only. Assertions read the
MCP tool or resource output, or a public service route.
"""

import asyncio
import json
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI, Request
from gateway_mcp.clients import ServiceClient
from gateway_mcp.clients.caller import caller_bearer
from gateway_mcp.server import mcp
from mcp.shared.exceptions import McpError
from mcp.types import CallToolResult
from the_watcher.main import app as watcher_app

from tests.helpers.live_services import closed_port_url, serve, unavailable_app
from tests.helpers.mcp_http import call_tool_over_http, read_resource_over_http, serve_mcp
from tests.helpers.watcher_engine import select_worker_engine
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


def _fake_worker() -> FastAPI:
    """Fake inference worker. Narrates from the request it receives, so output follows input."""
    app = FastAPI()

    @app.post("/inference/v1/dm-narration")
    async def _narrate(payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "narration": (
                f"[{payload['session_id']}] {payload['guidance_prompt']} "
                f"in {payload['scene_environment']}"
            ),
            "sensory_details": ["cold air"],
            "suggested_dm_prompts": ["Ask who lit the torch."],
            "tension_level": "rising",
            "source": "llm",
            "degraded": False,
        }

    return app


def _echo_authorization_app() -> FastAPI:
    """Fake board_state that answers with the Authorization header it received."""
    app = FastAPI()

    @app.get("/api/v1/boards/{session_id}")
    async def _board(session_id: str, request: Request) -> dict[str, Any]:
        return {"session_id": session_id, "authorization": request.headers.get("authorization")}

    return app


@pytest.fixture(scope="module")
def upstreams() -> Iterator[dict[str, str]]:
    """Run the owning services as real HTTP servers for the orchestration and resource tools."""
    from board_state.main import app as board_app
    from game_session.main import app as session_app
    from rules_compendium.main import app as compendium_app

    with (
        serve(watcher_app) as watcher_url,
        serve(session_app) as session_url,
        serve(board_app) as board_url,
        serve(compendium_app, lifespan="on") as compendium_url,
    ):
        yield {
            "watcher": watcher_url,
            "session": session_url,
            "board": board_url,
            "compendium": compendium_url,
        }


@pytest.fixture
def services(upstreams: dict[str, str], monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Point the gateway at the live upstream services for one test."""
    monkeypatch.setenv("THE_WATCHER_URL", upstreams["watcher"])
    monkeypatch.setenv("GAME_SESSION_URL", upstreams["session"])
    monkeypatch.setenv("BOARD_STATE_URL", upstreams["board"])
    monkeypatch.setenv("RULES_COMPENDIUM_URL", upstreams["compendium"])
    return upstreams


def _create_session(session_url: str, title: str) -> str:
    """Create a game session through the game_session public route and return its id."""
    with httpx.Client(base_url=session_url, headers=bearer("user-test")) as http:
        created = http.post(
            "/api/v1/sessions/create",
            json={"campaign_id": _owned_campaign(http), "title": title, "dm_id": "the_watcher"},
        )
        assert created.status_code == 200, created.text
        return str(created.json()["session_id"])


_MCP: dict[str, str] = {}


def bearer(sub: str) -> dict[str, str]:
    """Return the Authorization header for a token that the shared test issuer signs for `sub`."""
    return {"Authorization": f"Bearer {caller_token(sub)}"}


def caller_token(sub: str = "user-test") -> str:
    """Return a token that the shared test issuer signs for `sub`."""
    return SIGNING_ISSUER.mint(sub)


@pytest.fixture(scope="module", autouse=True)
def mcp_endpoint() -> Iterator[None]:
    """Serve the gateway MCP server over HTTP so each call carries the caller bearer."""
    with serve_mcp(mcp) as endpoint:
        _MCP["url"] = endpoint
        yield
    _MCP.clear()


async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
    """Call a tool over MCP HTTP as the `user-test` caller."""
    return await call_tool_over_http(_MCP["url"], name, arguments, caller_token())


async def read_resource(uri: str) -> str:
    """Read a resource over MCP HTTP as the `user-test` caller and return its JSON text."""
    return await read_resource_over_http(_MCP["url"], uri, caller_token())


def tool_text(result: CallToolResult) -> str:
    assert result.content, "Tool result must contain content"
    return str(result.content[0].text)


def tool_payload(result: CallToolResult) -> dict[str, Any]:
    assert not result.isError, f"Tool failed: {tool_text(result)}"
    data = json.loads(tool_text(result))
    assert isinstance(data, dict)
    return data


def narrate_arguments(session_id: str, scene_prompt: str) -> dict[str, Any]:
    return {
        "campaign_id": str(uuid4()),
        "session_id": session_id,
        "scene_prompt": scene_prompt,
        "player_actions": "Valeros kicks open the gate",
        "scene_environment": "Forgotten Library",
        "tone": "tense_mystery",
    }


# ---------------------------------------------------------------------------
# narrate_with_the_watcher calls The Watcher narration route
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_blackbox_narration_comes_from_the_watcher_and_follows_session(
    services: dict[str, str], monkeypatch: pytest.MonkeyPatch
):
    """Verify two sessions get two different narrations, produced by The Watcher route."""
    first = _create_session(services["session"], "Gate of Ash")
    second = _create_session(services["session"], "Drowned Vault")
    with serve(_fake_worker()) as worker_url:
        select_worker_engine(monkeypatch, worker_url)
        narrated_first = tool_payload(
            await call_tool("narrate_with_the_watcher", narrate_arguments(first, "Gate"))
        )
        narrated_second = tool_payload(
            await call_tool("narrate_with_the_watcher", narrate_arguments(second, "Vault"))
        )

    assert narrated_first["session_id"] == first
    assert narrated_second["session_id"] == second
    assert narrated_first["narrative"] != narrated_second["narrative"]
    assert narrated_first["narrative"].startswith(f"[{first}]")
    assert narrated_second["narrative"].startswith(f"[{second}]")
    assert narrated_first["source"] == "llm"


@pytest.mark.asyncio
async def test_blackbox_narration_worker_unavailable_returns_tool_error(
    services: dict[str, str], monkeypatch: pytest.MonkeyPatch
):
    """Verify a failed inference worker gives an MCP error, not a template narration."""
    session_id = _create_session(services["session"], "Silent Hall")
    with serve(unavailable_app(503)) as worker_url:
        select_worker_engine(monkeypatch, worker_url)
        result = await call_tool("narrate_with_the_watcher", narrate_arguments(session_id, "Hall"))

    assert result.isError


# ---------------------------------------------------------------------------
# Session and encounter resources read the owning services
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_blackbox_session_resource_returns_the_created_session(services: dict[str, str]):
    """Verify session://{id}/state returns the session created through game_session."""
    session_id = _create_session(services["session"], "Ambush at Red Larch")

    data = json.loads(await read_resource(f"session://{session_id}/state"))

    assert data["session_id"] == session_id
    assert data["title"] == "Ambush at Red Larch"
    assert data["status"] == "lobby"


@pytest.mark.asyncio
async def test_blackbox_session_resource_unknown_session_is_error(services: dict[str, str]):
    """Verify an unknown session id fails the resource read. No fixed session is returned."""
    with pytest.raises(McpError, match="Error creating resource from template"):
        await read_resource(f"session://{uuid4()}/state")


@pytest.mark.asyncio
async def test_blackbox_encounter_resource_returns_tokens_from_board_state(
    services: dict[str, str],
):
    """Verify encounter://{id}/current returns the tokens that board_state stores for the id."""
    session_id = _create_session(services["session"], "Red Larch Encounter")
    with httpx.Client(base_url=services["board"], headers=bearer("user-test")) as http:
        created = http.post(
            "/api/v1/boards",
            json={"campaign_id": BOARD_CAMPAIGN, "session_id": session_id, "cols": 10, "rows": 8},
        )
        assert created.status_code == 200, created.text
        placed = http.post(
            f"/api/v1/boards/{session_id}/tokens",
            json={"token_id": "goblin-9", "name": "Goblin Sentry", "x": 5, "y": 2},
        )
        assert placed.status_code == 200, placed.text

    data = json.loads(await read_resource(f"encounter://{session_id}/current"))

    assert data["session_id"] == session_id
    assert [(t["name"], t["x"], t["y"]) for t in data["tokens"]] == [("Goblin Sentry", 5, 2)]


@pytest.mark.asyncio
async def test_blackbox_encounter_resource_unknown_board_is_error(services: dict[str, str]):
    """Verify an unknown encounter id fails the read. game_session answers 404."""
    with pytest.raises(McpError, match="Error creating resource from template"):
        await read_resource(f"encounter://{uuid4()}/current")


# ---------------------------------------------------------------------------
# execute_agent_action_plan proposes each step to The Watcher action route
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_blackbox_action_plan_steps_are_proposed_to_the_watcher(services: dict[str, str]):
    """Verify each plan step returns the pending action The Watcher stored for it."""
    session_id = _create_session(services["session"], "Goblin Warren")
    campaign_id = str(uuid4())
    plan = [
        {
            "tool": "move_board_token",
            "actor_name": "Goblin Archer",
            "description": "Slip behind the barrels",
            "parameters": {"token_id": "goblin-1", "to_x": 3, "to_y": 4},
        },
        {
            "tool": "roll_dice",
            "actor_name": "Goblin Archer",
            "parameters": {"notation": "1d20+3", "reason": "Stealth"},
        },
    ]

    result = tool_payload(
        await call_tool(
            "execute_agent_action_plan",
            {"session_id": session_id, "campaign_id": campaign_id, "actions": plan},
        )
    )

    assert result["success"] is True
    assert result["completed_steps"] == 2
    first = result["steps"][0]["output"]
    assert first["session_id"] == session_id
    assert first["campaign_id"] == campaign_id
    assert first["action_type"] == "move_board_token"
    assert first["actor_name"] == "Goblin Archer"
    assert first["description"] == "Slip behind the barrels"
    assert result["steps"][1]["output"]["action_type"] == "roll_dice"


@pytest.mark.asyncio
async def test_blackbox_action_plan_unknown_tool_is_rejected_before_watcher(
    services: dict[str, str],
):
    """Verify an unknown tool name fails the step without any call to The Watcher."""
    session_id = str(uuid4())
    plan = [
        {
            "tool": "nonexistent_secret_spell_destroy_everything",
            "actor_name": "Valeros",
            "parameters": {"target": "all"},
        }
    ]

    result = tool_payload(
        await call_tool(
            "execute_agent_action_plan",
            {"session_id": session_id, "campaign_id": str(uuid4()), "actions": plan},
        )
    )

    assert result["status"] == "error"
    assert result["completed_steps"] == 0
    assert "nonexistent_secret_spell_destroy_everything" in result["error"]


@pytest.mark.asyncio
async def test_blackbox_action_plan_watcher_unreachable_is_step_error(
    services: dict[str, str], monkeypatch: pytest.MonkeyPatch
):
    """Verify an unreachable The Watcher fails the step with an error. No step reports success."""
    monkeypatch.setenv("THE_WATCHER_URL", closed_port_url())
    plan = [
        {
            "tool": "roll_dice",
            "actor_name": "Kyra",
            "parameters": {"notation": "1d20", "reason": "Check"},
        }
    ]

    result = tool_payload(
        await call_tool(
            "execute_agent_action_plan",
            {"session_id": str(uuid4()), "campaign_id": str(uuid4()), "actions": plan},
        )
    )

    assert result["status"] == "error"
    assert result["steps"][0]["status"] == "error"
    assert result["completed_steps"] == 0


# ---------------------------------------------------------------------------
# query_monster_stat_block calls rules_compendium, not local SRD data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_blackbox_monster_stat_block_comes_from_rules_compendium(services: dict[str, str]):
    """Verify the monster tool returns the stat block that rules_compendium serves."""
    payload = tool_payload(await call_tool("query_monster_stat_block", {"monster_name": "Bugbear"}))

    assert payload["status"] == "success"
    assert payload["monster"]["name"] == "Bugbear"
    assert payload["monster"]["challenge_rating"] == 1.0


@pytest.mark.asyncio
async def test_blackbox_monster_stat_block_unknown_name_is_tool_error(services: dict[str, str]):
    """Verify an unknown monster gives an MCP error, not a local lookup result."""
    result = await call_tool("query_monster_stat_block", {"monster_name": "Dragon of Nowhere"})
    assert result.isError


@pytest.mark.asyncio
async def test_blackbox_monster_stat_block_compendium_down_is_tool_error(
    services: dict[str, str], monkeypatch: pytest.MonkeyPatch
):
    """Verify a down rules_compendium gives an MCP error. The tool does not scan local data."""
    monkeypatch.setenv("RULES_COMPENDIUM_URL", closed_port_url())
    result = await call_tool("query_monster_stat_block", {"monster_name": "Bugbear"})
    assert result.isError


# ---------------------------------------------------------------------------
# Caller bearer is forwarded to the upstream service
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_blackbox_service_client_forwards_bearer_to_upstream():
    """Verify the shared client sends the caller bearer and no other credential."""
    from gateway_mcp.settings import GatewayMcpSettings

    with serve(_echo_authorization_app()) as board_url:
        settings = GatewayMcpSettings(board_state_url=board_url)
        with_token = await ServiceClient(settings, bearer="token-abc").get_board("s-1")
        without_token = await ServiceClient(settings).get_board("s-1")

    assert with_token["authorization"] == "Bearer token-abc"
    assert without_token["authorization"] is None


def test_blackbox_caller_bearer_reads_authorization_header_of_mcp_request():
    """Verify the bearer comes from the MCP request headers and is absent without a request."""
    from types import SimpleNamespace

    with_header = SimpleNamespace(
        request_context=SimpleNamespace(
            request=SimpleNamespace(headers={"authorization": "Bearer token-xyz"})
        )
    )
    no_request = SimpleNamespace(request_context=SimpleNamespace(request=None))
    basic_scheme = SimpleNamespace(
        request_context=SimpleNamespace(
            request=SimpleNamespace(headers={"authorization": "Basic x"})
        )
    )

    assert caller_bearer(with_header) == "token-xyz"
    assert caller_bearer(no_request) is None
    assert caller_bearer(basic_scheme) is None
    assert caller_bearer(None) is None


def _owned_campaign(client) -> str:
    """Create a campaign as the calling user, so that the caller can run sessions in it."""
    res = client.post("/api/v1/campaigns", json={"title": "Owned Campaign"})
    assert res.status_code == 201, res.text
    return res.json()["id"]


BOARD_CAMPAIGN = "camp-board-fixture"


@pytest.fixture(autouse=True)
def _board_campaign_dm(spicedb):
    """Make `user-test` the DM of the campaign that every board in this module belongs to."""
    asyncio.run(
        spicedb.write_relationship(
            resource_type="campaign",
            resource_id=BOARD_CAMPAIGN,
            relation="dungeon_master",
            subject_type="user",
            subject_id="user-test",
        )
    )
