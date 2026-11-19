"""Blackbox TDD tests for create_encounter reading a homebrew monster's CR by campaign (TASK-0800).

The MCP tool passes its campaign to rules_compendium. A homebrew monster of that campaign
resolves, and its challenge rating reaches game_session. Setup uses public routes only:
the DM registers the homebrew monster through the compendium frontdoor, and the MCP tools
are called over streamable HTTP with a signed caller bearer.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import httpx
import pytest
from mcp.types import CallToolResult
from runefoble_auth.mock import MockSpiceDBClient

from tests.helpers.game_session_setup import start_session_with_player
from tests.helpers.live_services import serve
from tests.helpers.mcp_http import call_tool_over_http, serve_mcp
from tests.helpers.spicedb_factory import shared_spicedb_client
from tests.helpers.ws_identity import SIGNING_ISSUER, bearer

CAMPAIGN = str(uuid4())
OTHER_CAMPAIGN = str(uuid4())
HOMEBREW_MONSTER = "Abyssal Shadowstalker"
HOMEBREW_CR = 3.0

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
def homebrew_upstreams() -> Iterator[dict[str, str]]:
    """Run game_session, board_state, and rules_compendium as real HTTP services for the gateway."""
    from board_state.main import app as board_app
    from game_session.main import app as session_app
    from game_session.shared.identity import (
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
            yield {"session": session_url, "compendium": compendium_url}
    finally:
        set_zitadel_auth_service(previous_verifier)


@pytest.fixture
def homebrew_monster(homebrew_upstreams: dict[str, str]) -> Iterator[None]:
    """Register the homebrew monster of `CAMPAIGN` through the compendium frontdoor, for one test.

    `user-test` is the DM of `CAMPAIGN` in the shared SpiceDB double. The factory client is
    swapped per test, so the grant is written in this fixture, for the test that uses it.
    """
    campaign_roles = MockSpiceDBClient()
    asyncio.run(
        campaign_roles.write_relationship(
            resource_type="campaign",
            resource_id=CAMPAIGN,
            relation="dungeon_master",
            subject_type="user",
            subject_id="user-test",
        )
    )
    with (
        shared_spicedb_client(campaign_roles),
        httpx.Client(
            base_url=homebrew_upstreams["compendium"], headers=bearer("user-test")
        ) as http,
    ):
        registered = http.post(
            "/api/v1/compendium/homebrew",
            json={
                "campaign_id": CAMPAIGN,
                "rule_type": "monster",
                "title": HOMEBREW_MONSTER,
                "content": {"challenge_rating": HOMEBREW_CR, "hit_points": 45},
            },
        )
        assert registered.status_code == 200, registered.text
        yield


async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
    """Call an MCP tool over HTTP as the DM of the started session (`user-test`)."""
    return await call_tool_over_http(_MCP["url"], name, arguments, bearer_token("user-test"))


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


def _turn_order_cr(combat: dict[str, Any], name: str) -> Any:
    """Read the challenge rating that game_session stored for one combatant of the encounter."""
    [combatant] = [c for c in combat["initiative_order"] if c["name"] == name]
    return combatant.get("cr")


@pytest.mark.asyncio
async def test_blackbox_create_encounter_reads_homebrew_cr_of_its_campaign(
    homebrew_upstreams: dict[str, str], homebrew_monster: None
):
    """Verify an enemy without a rating gets the CR of the homebrew monster of the named campaign."""
    session_id = start_session_with_player(homebrew_upstreams["session"])
    created = tool_payload(
        await call_tool(
            "create_encounter",
            {
                "session_id": session_id,
                "campaign_id": CAMPAIGN,
                "enemies": [{"name": HOMEBREW_MONSTER, "x": 2, "y": 2}],
            },
        )
    )
    assert created["encounter_id"] == session_id
    with httpx.Client(base_url=homebrew_upstreams["session"], headers=bearer("user-test")) as http:
        combat = http.get(f"/api/v1/sessions/{session_id}/combat")
    assert combat.status_code == 200, combat.text
    assert _turn_order_cr(combat.json(), HOMEBREW_MONSTER) == HOMEBREW_CR


@pytest.mark.asyncio
async def test_blackbox_create_encounter_homebrew_monster_is_not_found_in_other_campaign(
    homebrew_upstreams: dict[str, str], homebrew_monster: None
):
    """Verify a homebrew monster does not resolve for a campaign that did not register it."""
    session_id = start_session_with_player(homebrew_upstreams["session"])
    result = await call_tool(
        "create_encounter",
        {
            "session_id": session_id,
            "campaign_id": OTHER_CAMPAIGN,
            "enemies": [{"name": HOMEBREW_MONSTER, "x": 2, "y": 2}],
        },
    )
    assert result.isError is True
    assert "challenge rating" in tool_text(result).lower()
