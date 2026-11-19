"""Blackbox chain test: a spoken move reaches the board only through preview and player confirm (TASK-0814).

Governed by the design rule "The Watcher proposes; only the player's `confirm_move` commits a
board move" (AGENTS.md, ADR-0015). The chain runs through public frontdoors: the gateway
speak-and-act route, the live The Watcher and board_state upstreams, and the board WebSocket.
The board socket enters the in-process `board_state` app through the TestClient. Setup uses
public routes only (ADR-0014, Hard Invariant 7).
"""

from __future__ import annotations

from collections.abc import Iterator

import httpx
import pytest
from board_state.main import app as board_app
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from the_watcher.main import app as watcher_app

from tests.helpers.live_services import closed_port_url, serve
from tests.helpers.spectator_table import open_board_table
from tests.helpers.ws_identity import ws_subprotocols
from tests.realtime_session import bearer

SPEAK_PATH = "/api/v1/watcher/speak-and-act"
GOBLIN = "t_goblin"
GOBLIN_START = (6, 2)
DM = "dm_dora"
TRANSCRIPT = "move 2 squares west"
GOBLIN_TARGET = (4, 2)


@pytest.fixture
def watcher_url(monkeypatch: pytest.MonkeyPatch, board_state_upstream: str) -> Iterator[str]:
    """Serve The Watcher. Its board_state URL comes from the live `board_state_upstream`."""
    with serve(watcher_app) as url:
        monkeypatch.setenv("RUNEFOBLE_WATCHER_URL", url)
        yield url


@pytest.fixture
def gateway(
    watcher_url: str,
    game_session_upstream: str,
    board_state_upstream: str,
    character_sheet_upstream: str,
    voice_agent_upstream: str,
) -> Iterator[TestClient]:
    """The gateway, started after the Watcher and board upstreams are set."""
    with TestClient(gateway_app) as client:
        yield client


@pytest.fixture
def table(
    gateway: TestClient, game_session_upstream: str, board_state_upstream: str
) -> tuple[str, str]:
    """A campaign with a DM and a board that holds the goblin token at (6, 2)."""
    return open_board_table(
        gateway, game_session_upstream, board_state_upstream, DM, {"player_pip": "player"}
    )


@pytest.fixture
def board_socket(trusted_ws_issuer) -> TestClient:
    """The board app in-process. Its WebSocket shares the broadcast registry with the upstream."""
    return TestClient(board_app)


def _speech(session_id: str, campaign_id: str) -> dict[str, object]:
    return {
        "speaker_id": DM,
        "speaker_name": "Goblin Stalker",
        "transcript": TRANSCRIPT,
        "session_id": session_id,
        "campaign_id": campaign_id,
        "token_id": GOBLIN,
        "from_x": GOBLIN_START[0],
        "from_y": GOBLIN_START[1],
        "grid_cols": 8,
        "grid_rows": 8,
    }


def _position(board_url: str, session_id: str) -> tuple[int, int]:
    board = httpx.get(f"{board_url}/api/v1/boards/{session_id}", headers=bearer(DM))
    assert board.status_code == 200, board.text
    token = board.json()["tokens"][GOBLIN]
    return token["x"], token["y"]


def test_spoken_move_reaches_the_board_socket_as_a_preview_and_commits_on_confirm(
    gateway: TestClient,
    table: tuple[str, str],
    board_state_upstream: str,
    board_socket: TestClient,
) -> None:
    """Speak-and-act stages a preview on the board socket. Only `confirm_move` commits it."""
    campaign_id, session_id = table

    with board_socket.websocket_connect(
        f"/ws/boards/{session_id}", subprotocols=ws_subprotocols(DM)
    ) as ws:
        assert ws.receive_json()["type"] == "connected"

        spoken = gateway.post(SPEAK_PATH, json=_speech(session_id, campaign_id), headers=bearer(DM))
        assert spoken.status_code == 200, spoken.text
        assert spoken.json()["action_type"] == "move"

        preview = ws.receive_json()
        assert preview["type"] == "ghost_preview"
        assert preview["status"] == "staged"
        assert preview["preview"]["token_id"] == GOBLIN
        assert (preview["preview"]["to_x"], preview["preview"]["to_y"]) == GOBLIN_TARGET

        # The proposal does not move the token.
        assert _position(board_state_upstream, session_id) == GOBLIN_START

        ws.send_json({"action": "confirm_move", "token_id": GOBLIN, "to_x": 4, "to_y": 2})
        moved = ws.receive_json()

    assert moved["type"] == "token_moved"
    assert moved["status"] == "confirmed"
    assert _position(board_state_upstream, session_id) == GOBLIN_TARGET


def test_speak_and_act_without_confirm_leaves_the_token_where_it_was(
    gateway: TestClient,
    table: tuple[str, str],
    board_state_upstream: str,
    board_socket: TestClient,
) -> None:
    """A staged preview that the player never confirms does not change the board."""
    campaign_id, session_id = table

    with board_socket.websocket_connect(
        f"/ws/boards/{session_id}", subprotocols=ws_subprotocols(DM)
    ) as ws:
        ws.receive_json()
        spoken = gateway.post(SPEAK_PATH, json=_speech(session_id, campaign_id), headers=bearer(DM))
        assert spoken.status_code == 200, spoken.text
        assert ws.receive_json()["type"] == "ghost_preview"

    assert _position(board_state_upstream, session_id) == GOBLIN_START


def test_speak_and_act_fails_when_board_state_is_unreachable(
    gateway: TestClient,
    table: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A move the board cannot stage is an error. The Watcher does not report success.

    The Watcher answers 503 naming board_state. The gateway reports the failed upstream as
    its own error (ADR-0015 b). The response carries no parsed intent.
    """
    campaign_id, session_id = table
    monkeypatch.setenv("RUNEFOBLE_BOARD_STATE_URL", closed_port_url())

    spoken = gateway.post(SPEAK_PATH, json=_speech(session_id, campaign_id), headers=bearer(DM))

    assert spoken.status_code in (502, 503), spoken.text
    assert spoken.json().get("upstream") == "the_watcher"
    assert "action_type" not in spoken.text
