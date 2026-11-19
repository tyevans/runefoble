"""Blackbox TDD tests for the MCP create_encounter tool (TASK-0686, TASK-0885).

create_encounter reads each enemy rating from rules_compendium, then makes one write to the
game_session owner route that starts combat. board_state consumes that event from the session
stream and places the tokens. The encounter id is the game session id.

Setup and assertions use public HTTP routes of game_session, board_state and rules_compendium,
and the MCP tools are called over streamable HTTP with a signed caller bearer. Redis is an
external process. Every service publish goes to the in-memory bus that the board consumer reads.
"""

import json
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import httpx
import pytest
import redis.asyncio
from mcp.types import CallToolResult

from tests.helpers.game_session_setup import start_session_with_player
from tests.helpers.live_services import serve, unavailable_app
from tests.helpers.mcp_http import call_tool_over_http, serve_mcp
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.polling import wait_until
from tests.helpers.ws_identity import SIGNING_ISSUER, bearer

pytestmark = pytest.mark.usefixtures("board_campaign")

_MCP: dict[str, str] = {}


@pytest.fixture(scope="module", autouse=True)
def mcp_endpoint() -> Iterator[None]:
    """Serve the gateway MCP server over HTTP so each call carries the caller bearer."""
    with serve_mcp() as endpoint:
        _MCP["url"] = endpoint
        yield
    _MCP.clear()


@pytest.fixture(scope="module")
def compendium_url() -> Iterator[str]:
    """Run rules_compendium as a real HTTP service. The gateway reads enemy ratings from it."""
    from rules_compendium.main import app as compendium_app

    with serve(compendium_app, lifespan="on") as url:
        yield url


@pytest.fixture
def mock_redis(monkeypatch: pytest.MonkeyPatch, mock_bus: MockAsyncRedis) -> MockAsyncRedis:
    """Give the board_state lifespan the same in-memory Redis the services publish to."""
    monkeypatch.setattr(redis.asyncio, "from_url", lambda *_a, **_k: mock_bus)
    return mock_bus


@pytest.fixture
def wired(
    mock_redis: MockAsyncRedis, compendium_url: str, monkeypatch: pytest.MonkeyPatch
) -> Iterator[dict[str, str]]:
    """Run game_session and board_state as live services and point the gateway at them.

    board_state starts its stream consumers, so it runs with its lifespan on.
    """
    from board_state.main import app as board_app
    from game_session.shared.identity import (
        get_zitadel_auth_service,
        set_zitadel_auth_service,
    )

    from tests.helpers.game_session_app import session_app

    previous = get_zitadel_auth_service()
    set_zitadel_auth_service(SIGNING_ISSUER.verifier())
    try:
        with serve(board_app, lifespan="on") as board_url, serve(session_app) as session_url:
            monkeypatch.setenv("RUNEFOBLE_BOARD_STATE_URL", board_url)
            monkeypatch.setenv("RUNEFOBLE_GAME_SESSION_URL", session_url)
            monkeypatch.setenv("RUNEFOBLE_RULES_COMPENDIUM_URL", compendium_url)
            yield {"board": board_url, "session": session_url}
    finally:
        set_zitadel_auth_service(previous)


def board_status(board_url: str, session_id: str) -> int:
    """Read the board for a session through board_state and return the HTTP status."""
    with httpx.Client(base_url=board_url, headers=bearer("user-test")) as http:
        return http.get(f"/api/v1/boards/{session_id}").status_code


def board_tokens(board_url: str, session_id: str) -> list[dict[str, Any]] | None:
    """Return the tokens of a session board, or None when board_state has no board yet."""
    with httpx.Client(base_url=board_url, headers=bearer("user-test")) as http:
        response = http.get(f"/api/v1/boards/{session_id}")
        if response.status_code == 404:
            return None
        assert response.status_code == 200, response.text
        return list(response.json()["tokens"].values())


def session_campaign(session_url: str, session_id: str) -> str:
    """Read the campaign of a session through game_session. The board of a session belongs to it."""
    with httpx.Client(base_url=session_url, headers=bearer("user-test")) as http:
        response = http.get(f"/api/v1/sessions/{session_id}")
        assert response.status_code == 200, response.text
        return str(response.json()["campaign_id"])


def in_combat(session_url: str, session_id: str) -> bool:
    """Read the combat state of a session through game_session."""
    with httpx.Client(base_url=session_url, headers=bearer("user-test")) as http:
        response = http.get(f"/api/v1/sessions/{session_id}/combat")
        assert response.status_code == 200, response.text
        return bool(response.json()["in_combat"])


async def call_create_encounter(
    session_id: str,
    enemies: list[dict[str, Any]],
    board_campaign: str,
    caller: str = "user-test",
) -> CallToolResult:
    """Call create_encounter over MCP HTTP as `caller`. The DM of the session is `user-test`."""
    return await call_tool_over_http(
        _MCP["url"],
        "create_encounter",
        {"session_id": session_id, "campaign_id": board_campaign, "enemies": enemies},
        SIGNING_ISSUER.mint(caller),
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
async def test_blackbox_create_encounter_round_trips_to_query_encounter_state(
    wired: dict[str, str], board_campaign: str
):
    """Verify create_encounter starts combat, the board gets every token, and the query reads them."""
    session_id = start_session_with_player(wired["session"])

    created = await call_create_encounter(
        session_id,
        [
            {"name": "Goblin Archer", "x": 3, "y": 4, "hp": 7, "cr": 0.25},
            {"name": "Orc", "x": 6, "y": 2, "hp": 15, "cr": 2.0},
        ],
        board_campaign,
    )
    assert not created.isError, tool_text(created)
    payload: dict[str, Any] = json.loads(tool_text(created))
    assert payload["status"] == "encounter_created"
    assert payload["encounter_id"] == session_id
    assert payload["in_combat"] is True
    assert payload["round"] == 1
    assert [t["token_type"] for t in payload["enemies_spawned"]] == ["monster", "monster"]
    assert all(t["is_friendly"] is False for t in payload["enemies_spawned"])

    assert wait_until(
        lambda: bool(board_tokens(wired["board"], session_id)),
        timeout_s=5.0,
    )
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
async def test_blackbox_create_encounter_places_tokens_on_existing_board_of_session(
    wired: dict[str, str], board_campaign: str
):
    """Verify create_encounter places enemies on the board the session already has."""
    session_id = start_session_with_player(wired["session"])
    with httpx.Client(base_url=wired["board"], headers=bearer("user-test")) as http:
        existing = http.post(
            "/api/v1/boards",
            json={
                "campaign_id": session_campaign(wired["session"], session_id),
                "session_id": session_id,
                "cols": 12,
                "rows": 9,
            },
        )
        assert existing.status_code == 200, existing.text

    created = await call_create_encounter(
        session_id, [{"name": "Bandit", "x": 11, "y": 8, "cr": 0.125}], board_campaign
    )

    assert not created.isError, tool_text(created)
    assert json.loads(tool_text(created))["encounter_id"] == session_id
    assert wait_until(lambda: bool(board_tokens(wired["board"], session_id)), timeout_s=5.0)
    queried = await call_query_encounter_state(session_id)
    state: dict[str, Any] = json.loads(tool_text(queried))
    assert state["grid_dimensions"] == {"cols": 12, "rows": 9}
    assert [(t["name"], t["x"], t["y"]) for t in state["tokens"]] == [("Bandit", 11, 8)]


@pytest.mark.asyncio
async def test_blackbox_create_encounter_unknown_session_is_error_and_creates_no_board(
    wired: dict[str, str], board_campaign: str
):
    """Verify an unknown session id yields a tool error and no board is created for it."""
    unknown_session = str(uuid4())

    result = await call_create_encounter(
        unknown_session, [{"name": "Imp", "x": 0, "y": 0, "cr": 1.0}], board_campaign
    )

    assert result.isError is True
    assert board_status(wired["board"], unknown_session) == 404


@pytest.mark.asyncio
async def test_blackbox_create_encounter_game_session_503_is_error_not_encounter_id(
    wired: dict[str, str], monkeypatch: pytest.MonkeyPatch, board_campaign: str
):
    """Verify a game_session 503 yields an MCP error and no encounter id or board is returned."""
    session_id = start_session_with_player(wired["session"])
    with serve(unavailable_app(503)) as down_url:
        monkeypatch.setenv("RUNEFOBLE_GAME_SESSION_URL", down_url)
        result = await call_create_encounter(
            session_id, [{"name": "Imp", "x": 0, "y": 0, "cr": 1.0}], board_campaign
        )

    assert result.isError is True
    assert "game_session" in tool_text(result)
    assert "503" in tool_text(result)
    assert "encounter_id" not in tool_text(result)
    assert board_status(wired["board"], session_id) == 404


@pytest.mark.asyncio
async def test_blackbox_create_encounter_unknown_monster_starts_no_combat(
    wired: dict[str, str], board_campaign: str
):
    """Verify an enemy with no rating and no compendium stat block starts no combat."""
    session_id = start_session_with_player(wired["session"])

    result = await call_create_encounter(
        session_id, [{"name": "Nonexistent Beast Of Nowhere", "x": 1, "y": 1}], board_campaign
    )

    assert result.isError is True
    assert "challenge rating" in tool_text(result).lower()
    assert in_combat(wired["session"], session_id) is False
    assert board_status(wired["board"], session_id) == 404


@pytest.mark.asyncio
async def test_blackbox_create_encounter_refused_for_caller_without_session_control(
    wired: dict[str, str], board_campaign: str
):
    """Verify a caller who may not control the session gets a tool error and starts no combat."""
    session_id = start_session_with_player(wired["session"])

    result = await call_create_encounter(
        session_id,
        [{"name": "Goblin", "x": 1, "y": 1, "cr": 0.25}],
        board_campaign,
        caller=f"stranger-{uuid4()}",
    )

    assert result.isError is True
    assert in_combat(wired["session"], session_id) is False
