"""Blackbox TDD tests for the MCP query_encounter_state tool (TASK-0671).

Setup runs through public frontdoors only: game_session and board_state HTTP
routes served on loopback ports. The MCP tool reads round and turn order from
GET /api/v1/sessions/{session_id}/combat and tokens from board_state.
"""

import json
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import httpx
import pytest
from gateway_mcp.server import mcp
from mcp.shared.memory import create_connected_server_and_client_session
from mcp.types import CallToolResult

from tests.helpers.live_services import serve, unavailable_app
from tests.helpers.ws_identity import SIGNING_ISSUER

MCP_BEARER_GAP = (
    "TASK-0532/TASK-0623: MCP service calls send no caller bearer yet, "
    "so board_state and rules_compendium return 401"
)


def bearer(sub: str) -> dict[str, str]:
    """Return the Authorization header for a token that the shared test issuer signs for `sub`."""
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


@pytest.fixture(scope="module")
def upstreams() -> Iterator[dict[str, str]]:
    """Run game_session and board_state as real HTTP services."""
    from board_state.main import app as board_app
    from game_session.main import app as session_app

    with serve(board_app) as board_url, serve(session_app) as session_url:
        yield {"board": board_url, "session": session_url}


@pytest.fixture
def encounter(upstreams: dict[str, str], monkeypatch: pytest.MonkeyPatch) -> str:
    """Start combat through game_session, advance one turn, and place a board token."""
    monkeypatch.setenv("BOARD_STATE_URL", upstreams["board"])
    monkeypatch.setenv("GAME_SESSION_URL", upstreams["session"])

    with httpx.Client(base_url=upstreams["session"]) as http:
        created = http.post(
            "/api/v1/sessions/create",
            json={
                "campaign_id": str(uuid4()),
                "title": "Ambush at Red Larch",
                "dm_id": "the_watcher",
            },
        )
        assert created.status_code == 200, created.text
        session_id = created.json()["session_id"]

        for player_id, character_id, name, character_class in [
            ("player-1", str(uuid4()), "Valeros", "Fighter"),
            ("player-2", str(uuid4()), "Kyra", "Cleric"),
        ]:
            joined = http.post(
                f"/api/v1/sessions/{session_id}/join",
                json={
                    "player_id": player_id,
                    "character_id": character_id,
                    "character_name": name,
                    "character_class": character_class,
                },
            )
            assert joined.status_code == 200, joined.text
        assert http.post(f"/api/v1/sessions/{session_id}/start").status_code == 200
        started = http.post(f"/api/v1/sessions/{session_id}/combat/start")
        assert started.status_code == 200, started.text

        for combatant_id, combatant_name, score, is_npc in [
            ("npc-goblin-archer-1", "Goblin Archer", 15, True),
            ("kyra", "Kyra", 12, False),
            ("valeros", "Valeros", 20, False),
        ]:
            rolled = http.post(
                f"/api/v1/sessions/{session_id}/combat/initiative",
                json={
                    "combatant_id": combatant_id,
                    "combatant_name": combatant_name,
                    "initiative_score": score,
                    "is_npc": is_npc,
                },
            )
            assert rolled.status_code == 200, rolled.text

        advanced = http.post(
            f"/api/v1/sessions/{session_id}/combat/next-turn",
            json={"turn_seconds": 45},
        )
        assert advanced.status_code == 200, advanced.text

    with httpx.Client(base_url=upstreams["board"], headers=bearer("user-test")) as http:
        created_board = http.post(
            "/api/v1/boards", json={"session_id": session_id, "cols": 10, "rows": 8}
        )
        assert created_board.status_code == 200, created_board.text
        placed = http.post(
            f"/api/v1/boards/{session_id}/tokens",
            json={"token_id": "goblin-1", "name": "Goblin Archer", "x": 3, "y": 4},
        )
        assert placed.status_code == 200, placed.text

    return session_id


async def call_query_encounter_state(encounter_id: str) -> CallToolResult:
    """Call query_encounter_state through the MCP protocol with an in-memory client."""
    async with create_connected_server_and_client_session(mcp) as session:
        return await session.call_tool("query_encounter_state", {"encounter_id": encounter_id})


def tool_text(result: CallToolResult) -> str:
    assert result.content, "Tool result must contain content"
    return str(result.content[0].text)


@pytest.mark.xfail(strict=True, reason=MCP_BEARER_GAP)
@pytest.mark.asyncio
async def test_blackbox_query_encounter_state_returns_round_and_turn_order(encounter: str):
    """Verify the tool returns round 1, the ordered initiative list, and the second combatant as active."""
    result = await call_query_encounter_state(encounter)
    assert not result.isError, tool_text(result)
    payload: dict[str, Any] = json.loads(tool_text(result))

    assert payload["session_id"] == encounter
    assert payload["in_combat"] is True
    assert payload["round"] == 1
    assert [c["combatant_id"] for c in payload["turn_order"]] == [
        "valeros",
        "npc-goblin-archer-1",
        "kyra",
    ]
    assert payload["active_combatant_id"] == "npc-goblin-archer-1"
    assert [(t["name"], t["x"], t["y"]) for t in payload["tokens"]] == [("Goblin Archer", 3, 4)]


@pytest.mark.xfail(strict=True, reason=MCP_BEARER_GAP)
@pytest.mark.asyncio
async def test_blackbox_query_encounter_state_upstream_unavailable_returns_error(
    upstreams: dict[str, str], monkeypatch: pytest.MonkeyPatch
):
    """Verify a game_session 503 yields an MCP error result, not canned round or order data."""
    with httpx.Client(base_url=upstreams["board"], headers=bearer("user-test")) as http:
        session_id = str(uuid4())
        created_board = http.post(
            "/api/v1/boards", json={"session_id": session_id, "cols": 10, "rows": 8}
        )
        assert created_board.status_code == 200, created_board.text

    monkeypatch.setenv("BOARD_STATE_URL", upstreams["board"])
    with serve(unavailable_app(503)) as down_url:
        monkeypatch.setenv("GAME_SESSION_URL", down_url)
        result = await call_query_encounter_state(session_id)

    assert result.isError is True
    assert "game_session" in tool_text(result)
