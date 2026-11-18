"""Blackbox TDD tests for the MCP create_encounter tool (TASK-0686).

create_encounter starts combat through game_session. The encounter id is the game
session id. Setup and assertions use public HTTP routes of game_session and
board_state, and the MCP tools are called over streamable HTTP with a signed caller bearer.
"""

import asyncio
import json
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import httpx
import pytest
from gateway_mcp.server import mcp
from mcp.types import CallToolResult

from tests.helpers.game_session_setup import start_session_with_player
from tests.helpers.live_services import serve, unavailable_app
from tests.helpers.mcp_http import call_tool_over_http, serve_mcp
from tests.helpers.ws_identity import SIGNING_ISSUER

_MCP: dict[str, str] = {}


def bearer(sub: str) -> dict[str, str]:
    """Return the Authorization header for a token that the shared test issuer signs for `sub`."""
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


@pytest.fixture(scope="module", autouse=True)
def mcp_endpoint() -> Iterator[None]:
    """Serve the gateway MCP server over HTTP so each call carries the caller bearer."""
    with serve_mcp(mcp) as endpoint:
        _MCP["url"] = endpoint
        yield
    _MCP.clear()


@pytest.fixture(scope="module")
def upstreams() -> Iterator[dict[str, str]]:
    """Run game_session and board_state as real HTTP services. game_session trusts the test issuer."""
    from board_state.main import app as board_app
    from game_session.main import app as session_app
    from game_session.settlement.auth.tokens import (
        get_zitadel_auth_service,
        set_zitadel_auth_service,
    )

    previous = get_zitadel_auth_service()
    set_zitadel_auth_service(SIGNING_ISSUER.verifier())
    try:
        with serve(board_app) as board_url, serve(session_app) as session_url:
            yield {"board": board_url, "session": session_url}
    finally:
        set_zitadel_auth_service(previous)


@pytest.fixture
def wired(upstreams: dict[str, str], monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Point the gateway at the live game_session and board_state services."""
    monkeypatch.setenv("BOARD_STATE_URL", upstreams["board"])
    monkeypatch.setenv("GAME_SESSION_URL", upstreams["session"])
    return upstreams


def board_status(board_url: str, session_id: str) -> int:
    """Read the board for a session through board_state and return the HTTP status."""
    with httpx.Client(base_url=board_url, headers=bearer("user-test")) as http:
        return http.get(f"/api/v1/boards/{session_id}").status_code


async def call_create_encounter(session_id: str, enemies: list[dict[str, Any]]) -> CallToolResult:
    """Call create_encounter over MCP HTTP as the DM of the started session (`user-test`)."""
    return await call_tool_over_http(
        _MCP["url"],
        "create_encounter",
        {"session_id": session_id, "campaign_id": BOARD_CAMPAIGN, "enemies": enemies},
        SIGNING_ISSUER.mint("user-test"),
    )


async def call_query_encounter_state(encounter_id: str) -> CallToolResult:
    """Call query_encounter_state over MCP HTTP, with the `user-test` caller bearer."""
    return await call_tool_over_http(
        _MCP["url"],
        "query_encounter_state",
        {"encounter_id": encounter_id},
        SIGNING_ISSUER.mint("user-test"),
    )


def tool_text(result: CallToolResult) -> str:
    assert result.content, "Tool result must contain content"
    return str(result.content[0].text)


@pytest.mark.asyncio
async def test_blackbox_create_encounter_round_trips_to_query_encounter_state(wired):
    """Verify create_encounter starts combat in the session and query_encounter_state reads it back."""
    session_id = start_session_with_player(wired["session"])

    created = await call_create_encounter(
        session_id,
        [
            {"name": "Goblin Archer", "x": 3, "y": 4, "hp": 7, "cr": 0.25},
            {"name": "Orc", "x": 6, "y": 2, "hp": 15, "cr": 2.0},
        ],
    )
    assert not created.isError, tool_text(created)
    payload: dict[str, Any] = json.loads(tool_text(created))
    assert payload["status"] == "encounter_created"
    assert payload["encounter_id"] == session_id
    assert payload["in_combat"] is True
    assert payload["round"] == 1
    assert payload["grid"] == {"cols": 10, "rows": 8}
    assert [t["token_type"] for t in payload["enemies_spawned"]] == ["monster", "monster"]
    assert all(t["is_friendly"] is False for t in payload["enemies_spawned"])

    queried = await call_query_encounter_state(session_id)
    assert not queried.isError, tool_text(queried)
    state: dict[str, Any] = json.loads(tool_text(queried))
    assert state["session_id"] == session_id
    assert state["in_combat"] is True
    assert state["round"] == 1
    assert sorted((t["name"], t["x"], t["y"]) for t in state["tokens"]) == [
        ("Goblin Archer", 3, 4),
        ("Orc", 6, 2),
    ]
    assert all(t["token_type"] == "monster" for t in state["tokens"])


@pytest.mark.asyncio
async def test_blackbox_create_encounter_reuses_existing_board_of_session(wired):
    """Verify create_encounter places enemies on the board the session already has."""
    session_id = start_session_with_player(wired["session"])
    with httpx.Client(base_url=wired["board"], headers=bearer("user-test")) as http:
        existing = http.post(
            "/api/v1/boards",
            json={"campaign_id": BOARD_CAMPAIGN, "session_id": session_id, "cols": 12, "rows": 9},
        )
        assert existing.status_code == 200, existing.text

    created = await call_create_encounter(
        session_id, [{"name": "Bandit", "x": 1, "y": 1, "cr": 0.125}]
    )

    assert not created.isError, tool_text(created)
    payload: dict[str, Any] = json.loads(tool_text(created))
    assert payload["grid"] == {"cols": 12, "rows": 9}
    assert payload["encounter_id"] == session_id


@pytest.mark.asyncio
async def test_blackbox_create_encounter_unknown_session_is_error_and_creates_no_board(wired):
    """Verify an unknown session id yields a tool error and no board is created for it."""
    unknown_session = str(uuid4())

    result = await call_create_encounter(
        unknown_session, [{"name": "Imp", "x": 0, "y": 0, "cr": 1.0}]
    )

    assert result.isError is True
    assert board_status(wired["board"], unknown_session) == 404


@pytest.mark.asyncio
async def test_blackbox_create_encounter_game_session_503_is_error_not_board_id(
    wired: dict[str, str], monkeypatch: pytest.MonkeyPatch
):
    """Verify a game_session 503 yields an MCP error and no encounter id or board is returned."""
    session_id = start_session_with_player(wired["session"])
    with serve(unavailable_app(503)) as down_url:
        monkeypatch.setenv("GAME_SESSION_URL", down_url)
        result = await call_create_encounter(
            session_id, [{"name": "Imp", "x": 0, "y": 0, "cr": 1.0}]
        )

    assert result.isError is True
    assert "game_session" in tool_text(result)
    assert "503" in tool_text(result)
    assert "encounter_id" not in tool_text(result)
    assert board_status(wired["board"], session_id) == 404


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
    asyncio.run(
        spicedb.write_relationship(
            resource_type="campaign",
            resource_id=BOARD_CAMPAIGN,
            relation="dungeon_master",
            subject_type="user",
            subject_id="user-test",
        )
    )
