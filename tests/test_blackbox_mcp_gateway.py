"""Blackbox TDD integration test suite for FastMCP Gateway Server.

Tests exercise FastMCP public protocol entrypoints exclusively:
- Tool discovery and execution through the MCP streamable HTTP transport, with the
  caller's signed bearer on each MCP request ('tests/helpers/mcp_http.py')
- Tool discovery via MCP `tools/list`
- Error handling for invalid tools and out-of-bounds tactical grid movements
"""

import json
from collections.abc import Iterator
from typing import Any

import httpx
import pytest
from gateway_mcp.container import GatewayMcpContainer
from gateway_mcp.server import build_mcp
from mcp.types import CallToolResult
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.mock import MockSpiceDBClient
from runefoble_auth.sync import ZitadelSpiceDBSyncService
from runefoble_auth.sync_events import handle_domain_event

from tests.helpers.campaign_setup import create_campaign
from tests.helpers.game_session_setup import start_session_with_player
from tests.helpers.live_services import closed_port_url, serve, unavailable_app
from tests.helpers.mcp_http import call_tool_over_http, listed_tools, serve_mcp
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.service_harness import routed_event_bus
from tests.helpers.spicedb_factory import shared_spicedb_client
from tests.helpers.ws_identity import SIGNING_ISSUER, bearer

pytestmark = pytest.mark.usefixtures("board_campaign")

_MCP: dict[str, str] = {}


def bearer_token(sub: str) -> str:
    """Return a token that the shared test issuer signs for `sub`."""
    return SIGNING_ISSUER.mint(sub)


@pytest.fixture(scope="module", autouse=True)
def mcp_endpoint() -> Iterator[None]:
    """Serve the gateway MCP server over HTTP so each call carries the caller bearer."""
    with serve_mcp() as endpoint:
        _MCP["url"] = endpoint
        yield
    _MCP.clear()


@pytest.fixture(scope="module", autouse=True)
def owning_services() -> Iterator[dict[str, str]]:
    """Run game_session, board_state, and rules_compendium as real HTTP services for the gateway."""
    from board_state.main import app as board_app
    from game_session.main import app as session_app
    from game_session.settlement.auth.tokens import (
        get_zitadel_auth_service,
        set_zitadel_auth_service,
    )
    from rules_compendium.main import app as compendium_app

    previous_verifier = get_zitadel_auth_service()
    set_zitadel_auth_service(SIGNING_ISSUER.verifier())
    try:
        with (
            pytest.MonkeyPatch.context() as env,
            serve(board_app) as board_url,
            serve(session_app) as session_url,
            serve(compendium_app, lifespan="on") as compendium_url,
        ):
            env.setenv("RUNEFOBLE_BOARD_STATE_URL", board_url)
            env.setenv("RUNEFOBLE_GAME_SESSION_URL", session_url)
            env.setenv("RUNEFOBLE_RULES_COMPENDIUM_URL", compendium_url)
            # Setup through public frontdoors: the owner creates the campaign, then the board.
            campaign_roles = MockSpiceDBClient()
            with (
                routed_event_bus(MockAsyncRedis()),
                shared_spicedb_client(campaign_roles),
                httpx.Client(base_url=session_url, headers=bearer("user-test")) as game_http,
                httpx.Client(base_url=board_url, headers=bearer("user-test")) as http,
            ):
                campaign_id = create_campaign(game_http, "user-test")
                created = http.post(
                    "/api/v1/boards",
                    json={
                        "session_id": "camp1",
                        "campaign_id": campaign_id,
                        "cols": 10,
                        "rows": 10,
                    },
                )
                assert created.status_code == 200, created.text
                placed = http.post(
                    "/api/v1/boards/camp1/tokens",
                    json={"token_id": "t1", "name": "Valeros", "x": 1, "y": 1},
                )
                assert placed.status_code == 200, placed.text
            yield {
                "board": board_url,
                "compendium": compendium_url,
                "session": session_url,
            }
    finally:
        set_zitadel_auth_service(previous_verifier)


async def call_tool(
    name: str, arguments: dict[str, Any], caller: str = "user-test"
) -> CallToolResult:
    """Call a tool over MCP HTTP as `caller`. The DM of a started session is `user-test`."""
    return await call_tool_over_http(_MCP["url"], name, arguments, bearer_token(caller))


async def grant_token_to_campaign(session_url: str, session_id: str, token_id: str) -> None:
    """Publish the TokenPlaced event to the identity sync consumer, as board_state does.

    The consumer writes the `board_token` relations that `board_token.move` reads.
    """
    with httpx.Client(base_url=session_url, headers=bearer("user-test")) as http:
        campaign_id = http.get(f"/api/v1/sessions/{session_id}").json()["campaign_id"]
    await handle_domain_event(
        ZitadelSpiceDBSyncService(spicedb_client=get_spicedb_client()),
        {
            "event_type": "runefoble.events.board.token_placed",
            "token_id": token_id,
            "campaign_id": campaign_id,
        },
    )


def tool_text(result: CallToolResult) -> str:
    """Return the text of the first content block of a tool result."""
    assert result.content, "Tool result must contain content"
    return str(result.content[0].text)


def tool_payload(result: CallToolResult) -> dict[str, Any]:
    """Return the JSON payload of a successful tool result."""
    assert not result.isError, f"Tool failed: {tool_text(result)}"
    data = json.loads(tool_text(result))
    assert isinstance(data, dict)
    return data


@pytest.mark.asyncio
async def test_blackbox_execute_agent_action_plan_invalid_tool():
    """Verify error handling when action plan specifies an invalid or unknown tool."""
    plan = [
        {
            "tool": "nonexistent_secret_spell_destroy_everything",
            "parameters": {"target": "all"},
        }
    ]

    result = tool_payload(
        await call_tool(
            "execute_agent_action_plan",
            {"session_id": "camp1", "campaign_id": "camp1", "actions": plan},
        )
    )

    assert result["status"] == "error"
    assert result["success"] is False
    assert result["completed_steps"] == 0
    assert result["total_steps"] == 1
    assert "nonexistent_secret_spell_destroy_everything" in result["error"]
    assert len(result["steps"]) == 1
    assert result["steps"][0]["status"] == "error"


@pytest.mark.asyncio
async def test_blackbox_mcp_tool_discovery():
    """Verify public MCP discovery (`tools/list`) reveals all expected tools, including the orchestrator."""
    tool_map = await listed_tools(_MCP["url"])

    assert "execute_agent_action_plan" in tool_map
    plan_tool = tool_map["execute_agent_action_plan"]
    assert "actions" in plan_tool.inputSchema["properties"]
    assert "session_id" in plan_tool.inputSchema["properties"]


@pytest.mark.asyncio
async def test_blackbox_prompt_templates():
    """Verify prompt templates dm_narrative_guidance and tactical_action_adviser."""
    mcp = build_mcp(GatewayMcpContainer.default())
    prompts = await mcp.list_prompts()
    prompt_names = [p.name for p in prompts]
    assert "dm_narrative_guidance" in prompt_names
    assert "tactical_action_adviser" in prompt_names

    p1 = await mcp.get_prompt(
        "dm_narrative_guidance", arguments={"scene_context": "Ruined cathedral"}
    )
    assert "The Watcher" in p1.messages[0].content.text
    assert "Ruined cathedral" in p1.messages[0].content.text

    p2 = await mcp.get_prompt(
        "tactical_action_adviser", arguments={"tactical_situation": "Surrounded by goblins"}
    )
    assert "Tactical Action Adviser" in p2.messages[0].content.text
    assert "Surrounded by goblins" in p2.messages[0].content.text


@pytest.mark.asyncio
async def test_blackbox_create_encounter_stores_enemy_tokens(
    owning_services: dict[str, str], board_campaign: str
):
    """Verify create_encounter stores enemies on the board that inspect_tactical_board reads back."""
    session_id = start_session_with_player(owning_services["session"])
    created = tool_payload(
        await call_tool(
            "create_encounter",
            {
                "session_id": session_id,
                "campaign_id": board_campaign,
                "enemies": [{"name": "Bandit", "x": 4, "y": 4, "hp": 11}],
            },
            "user-test",
        )
    )
    assert created["status"] == "encounter_created"
    assert created["grid"] == {"cols": 10, "rows": 8}

    state = tool_payload(
        await call_tool("inspect_tactical_board", {"session_id": created["encounter_id"]})
    )
    assert state["grid_dimensions"] == {"cols": 10, "rows": 8}
    assert [(t["name"], t["x"], t["y"]) for t in state["tokens"]] == [("Bandit", 4, 4)]


def _turn_order_cr(state: dict[str, Any], name: str) -> Any:
    """Read the challenge rating that game_session stored for one combatant of the encounter."""
    [combatant] = [c for c in state["turn_order"] if c["name"] == name]
    return combatant.get("cr")


@pytest.mark.asyncio
async def test_blackbox_create_encounter_reads_missing_cr_from_compendium(
    owning_services: dict[str, str],
    board_campaign: str,
):
    """Verify an enemy without a rating gets the challenge rating of its rules_compendium stat block."""
    session_id = start_session_with_player(owning_services["session"])
    created = tool_payload(
        await call_tool(
            "create_encounter",
            {
                "session_id": session_id,
                "campaign_id": board_campaign,
                "enemies": [{"name": "Goblin", "x": 1, "y": 1}],
            },
            "user-test",
        )
    )
    state = tool_payload(
        await call_tool("query_encounter_state", {"encounter_id": created["encounter_id"]})
    )
    assert _turn_order_cr(state, "Goblin") == 0.25


@pytest.mark.asyncio
async def test_blackbox_create_encounter_request_cr_is_kept_over_compendium(
    owning_services: dict[str, str],
    board_campaign: str,
):
    """Verify a challenge rating given in the request is stored as given."""
    session_id = start_session_with_player(owning_services["session"])
    created = tool_payload(
        await call_tool(
            "create_encounter",
            {
                "session_id": session_id,
                "campaign_id": board_campaign,
                "enemies": [{"name": "Goblin", "x": 1, "y": 1, "cr": 2.0}],
            },
            "user-test",
        )
    )
    state = tool_payload(
        await call_tool("query_encounter_state", {"encounter_id": created["encounter_id"]})
    )
    assert _turn_order_cr(state, "Goblin") == 2.0


@pytest.mark.asyncio
async def test_blackbox_create_encounter_without_any_rating_is_validation_error(
    owning_services: dict[str, str],
    board_campaign: str,
):
    """Verify an enemy with no rating in the request or the compendium is refused, not scored as zero."""
    session_id = start_session_with_player(owning_services["session"])
    result = await call_tool(
        "create_encounter",
        {
            "session_id": session_id,
            "campaign_id": board_campaign,
            "enemies": [{"name": "Unlisted Horror", "x": 2, "y": 2}],
        },
        "user-test",
    )
    assert result.isError is True
    assert "challenge rating" in result.content[0].text.lower()


@pytest.mark.asyncio
async def test_blackbox_move_board_token_then_inspect_reports_new_position(
    owning_services: dict[str, str],
    board_campaign: str,
):
    """Verify a token moved through MCP is read back at its new position from the board."""
    combat_session_id = start_session_with_player(owning_services["session"])
    created = tool_payload(
        await call_tool(
            "create_encounter",
            {
                "session_id": combat_session_id,
                "campaign_id": board_campaign,
                "enemies": [{"name": "Goblin", "x": 2, "y": 2}],
            },
            "user-test",
        )
    )
    session_id = created["encounter_id"]
    token_id = created["enemies_spawned"][0]["token_id"]
    await grant_token_to_campaign(owning_services["session"], session_id, token_id)

    moved = tool_payload(
        await call_tool(
            "move_board_token",
            {"session_id": session_id, "token_id": token_id, "to_x": 6, "to_y": 2},
            "user-test",
        )
    )
    assert moved["status"] == "success"
    assert moved["destination"] == {"x": 6, "y": 2}

    board = tool_payload(await call_tool("inspect_tactical_board", {"session_id": session_id}))
    goblin = board["tokens"][0]
    assert (goblin["token_id"], goblin["x"], goblin["y"]) == (token_id, 6, 2)


@pytest.mark.asyncio
async def test_blackbox_move_board_token_out_of_bounds_is_error_result(
    owning_services: dict[str, str],
    board_campaign: str,
):
    """Verify the board rejects an out-of-bounds move and the MCP result reports an error."""
    combat_session_id = start_session_with_player(owning_services["session"])
    created = tool_payload(
        await call_tool(
            "create_encounter",
            {
                "session_id": combat_session_id,
                "campaign_id": board_campaign,
                "enemies": [{"name": "Imp", "x": 0, "y": 0, "cr": 1.0}],
            },
            "user-test",
        )
    )
    await grant_token_to_campaign(
        owning_services["session"],
        created["encounter_id"],
        created["enemies_spawned"][0]["token_id"],
    )
    result = await call_tool(
        "move_board_token",
        {
            "session_id": created["encounter_id"],
            "token_id": created["enemies_spawned"][0]["token_id"],
            "to_x": 99,
            "to_y": -5,
        },
        "user-test",
    )
    assert result.isError is True
    assert "bounds" in tool_text(result).lower()


@pytest.mark.asyncio
async def test_blackbox_inspect_board_returns_error_when_board_service_returns_503(monkeypatch):
    """Verify a 503 from board_state becomes an MCP error result, not canned board data."""
    with serve(unavailable_app(503)) as down_url:
        monkeypatch.setenv("RUNEFOBLE_BOARD_STATE_URL", down_url)
        result = await call_tool("inspect_tactical_board", {"session_id": "camp-503"})

    assert result.isError is True
    assert "503" in tool_text(result)
    assert "Valeros" not in tool_text(result)


@pytest.mark.asyncio
async def test_blackbox_inspect_board_returns_error_when_board_service_is_unreachable(monkeypatch):
    """Verify an unreachable board_state becomes an MCP error result, not canned board data."""
    monkeypatch.setenv("RUNEFOBLE_BOARD_STATE_URL", closed_port_url())
    result = await call_tool("inspect_tactical_board", {"session_id": "camp-down"})

    assert result.isError is True
    assert "unreachable" in tool_text(result)


@pytest.mark.asyncio
async def test_blackbox_calculate_encounter_balance_uses_rules_compendium_route():
    """Verify encounter balance is computed by the rules_compendium public route."""
    balance = tool_payload(
        await call_tool(
            "calculate_encounter_balance",
            {"party_levels": [3, 3, 3, 4], "target_difficulty": "Medium"},
        )
    )
    assert balance["party_size"] == 4
    assert balance["target_difficulty"] == "Medium"
    assert "difficulty_tier" in balance
    assert "encounter_id" in balance
    assert balance["total_monster_count"] == sum(m["count"] for m in balance["monsters"])


@pytest.mark.asyncio
async def test_blackbox_calculate_encounter_balance_rejects_empty_party():
    """Verify rules_compendium validation errors surface as MCP error results."""
    result = await call_tool(
        "calculate_encounter_balance",
        {"party_levels": [], "target_difficulty": "Medium"},
    )
    assert result.isError is True
    assert "rejected the request (422)" in tool_text(result)
