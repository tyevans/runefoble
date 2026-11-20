"""Blackbox tests: possessive and named-token spoken moves (TASK-0944, ADR-0022 a).

The grammar parses "move my warrior to the chest" as a move to the token named "chest". The
destination is the free neighbour of that token, resolved by TASK-0942. The mover is always the
speaker's own token (`token_id`). The chain runs through the public gateway speak-and-act route,
the live The Watcher and board_state upstreams, and the board WebSocket. Setup uses public routes
only (ADR-0014, Hard Invariant 7).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx
import pytest
from board_state.main import app as board_app
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app

from tests.helpers.live_services import serve
from tests.helpers.spectator_table import open_board_table
from tests.helpers.the_watcher_app import watcher_app
from tests.helpers.ws_identity import bearer, ws_subprotocols

SPEAK_PATH = "/api/v1/watcher/speak-and-act"
DM = "dm_dora"
VALEROS = "t1"
VALEROS_START = (2, 3)
CHEST = "t_chest"
CHEST_CELL = (6, 6)
# The free neighbours of (6, 6) nearest to (2, 3) are (5, 5), (5, 6) and (5, 7).
# Grid distance from (2, 3) is 3 for each. The tie goes to the lower y, so (5, 5) wins.
CHEST_NEIGHBOUR = (5, 5)
POSSESSIVE_SPEECH = (
    "move my warrior to the chest",
    "move the warrior to the chest",
    "move Valeros to the chest",
)


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
    """A campaign and board. Valeros (`t1`) stands at (2, 3). The goblin stands at (6, 2)."""
    return open_board_table(
        gateway, game_session_upstream, board_state_upstream, DM, {"player_pip": "player"}
    )


@pytest.fixture
def board_socket(trusted_ws_issuer) -> TestClient:
    """The board app in-process. Its WebSocket shares the broadcast registry with the upstream."""
    return TestClient(board_app)


def _place_token(board_url: str, session_id: str, token_id: str, name: str, x: int, y: int) -> None:
    """Place one token on the board through the public board route."""
    placed = httpx.post(
        f"{board_url}/api/v1/boards/{session_id}/tokens",
        json={"token_id": token_id, "name": name, "token_type": "npc", "x": x, "y": y, "hp": 5},
        headers=bearer(DM),
    )
    assert placed.status_code == 200, placed.text


def _speech(session_id: str, campaign_id: str, transcript: str) -> dict[str, Any]:
    """A speech body from Valeros's player, who speaks through Valeros's token."""
    return {
        "speaker_id": DM,
        "speaker_name": "Valeros",
        "transcript": transcript,
        "session_id": session_id,
        "campaign_id": campaign_id,
        "token_id": VALEROS,
        "from_x": VALEROS_START[0],
        "from_y": VALEROS_START[1],
        "grid_cols": 8,
        "grid_rows": 8,
    }


def _expect_next_frame_is_staged(
    gateway: TestClient, ws: Any, campaign_id: str, session_id: str, to: tuple[int, int]
) -> None:
    """A refused speech sends no frame. The next valid move must still stage its own preview."""
    body = _speech(session_id, campaign_id, "move to 4, 7")
    spoken = gateway.post(SPEAK_PATH, json=body, headers=bearer(DM))
    assert spoken.status_code == 200, spoken.text
    frame = ws.receive_json()
    assert frame["type"] == "ghost_preview"
    assert (frame["preview"]["to_x"], frame["preview"]["to_y"]) == to


@pytest.mark.parametrize("transcript", POSSESSIVE_SPEECH)
def test_possessive_move_stages_the_free_neighbour_of_the_named_token(
    gateway: TestClient,
    table: tuple[str, str],
    board_state_upstream: str,
    board_socket: TestClient,
    transcript: str,
) -> None:
    """The speaker's token is the mover. The preview goes next to the chest, and nothing moves."""
    campaign_id, session_id = table
    _place_token(board_state_upstream, session_id, CHEST, "Chest", *CHEST_CELL)
    body = _speech(session_id, campaign_id, transcript)

    with board_socket.websocket_connect(
        f"/ws/boards/{session_id}", subprotocols=ws_subprotocols(DM)
    ) as ws:
        ws.receive_json()
        spoken = gateway.post(SPEAK_PATH, json=body, headers=bearer(DM))
        assert spoken.status_code == 200, spoken.text
        assert spoken.json()["action_type"] == "move"
        preview = ws.receive_json()

    assert preview["type"] == "ghost_preview"
    assert preview["preview"]["token_id"] == VALEROS
    assert (preview["preview"]["to_x"], preview["preview"]["to_y"]) == CHEST_NEIGHBOUR
    board = httpx.get(f"{board_state_upstream}/api/v1/boards/{session_id}", headers=bearer(DM))
    assert board.json()["tokens"][VALEROS]["x"] == VALEROS_START[0]
    assert board.json()["tokens"][VALEROS]["y"] == VALEROS_START[1]


def test_possessive_move_without_token_id_is_a_client_error_and_stages_nothing(
    gateway: TestClient,
    table: tuple[str, str],
    board_state_upstream: str,
    board_socket: TestClient,
) -> None:
    """The mover is the speaker's token. Without `token_id` the Watcher answers 422."""
    campaign_id, session_id = table
    _place_token(board_state_upstream, session_id, CHEST, "Chest", *CHEST_CELL)
    body = _speech(session_id, campaign_id, POSSESSIVE_SPEECH[0])
    del body["token_id"]

    with board_socket.websocket_connect(
        f"/ws/boards/{session_id}", subprotocols=ws_subprotocols(DM)
    ) as ws:
        ws.receive_json()
        spoken = gateway.post(SPEAK_PATH, json=body, headers=bearer(DM))
        assert spoken.status_code == 422, spoken.text
        _expect_next_frame_is_staged(gateway, ws, campaign_id, session_id, to=(4, 7))


def test_possessive_move_to_a_name_two_tokens_share_is_a_conflict(
    gateway: TestClient,
    table: tuple[str, str],
    board_state_upstream: str,
    board_socket: TestClient,
) -> None:
    """Two tokens named "Chest" make the target ambiguous. The Watcher answers 409 and stages nothing.

    Disambiguation by the player is out of scope for release one (TASK-0944).
    """
    campaign_id, session_id = table
    _place_token(board_state_upstream, session_id, CHEST, "Chest", *CHEST_CELL)
    _place_token(board_state_upstream, session_id, "t_chest_2", "Chest", 0, 7)
    body = _speech(session_id, campaign_id, POSSESSIVE_SPEECH[0])

    with board_socket.websocket_connect(
        f"/ws/boards/{session_id}", subprotocols=ws_subprotocols(DM)
    ) as ws:
        ws.receive_json()
        spoken = gateway.post(SPEAK_PATH, json=body, headers=bearer(DM))
        assert spoken.status_code == 409, spoken.text
        _expect_next_frame_is_staged(gateway, ws, campaign_id, session_id, to=(4, 7))


def test_roll_a_d20_still_returns_roll_dice(gateway: TestClient, table: tuple[str, str]) -> None:
    """Regression: the dice phrase keeps its intent after the possessive shape is added."""
    campaign_id, session_id = table
    spoken = gateway.post(
        SPEAK_PATH, json=_speech(session_id, campaign_id, "roll a d20"), headers=bearer(DM)
    )

    assert spoken.status_code == 200, spoken.text
    assert spoken.json()["action_type"] == "roll_dice"
    assert spoken.json()["parameters"]["notation"] == "1d20"


def test_move_my_warrior_without_a_target_is_not_a_board_move(
    gateway: TestClient,
    table: tuple[str, str],
    board_state_upstream: str,
) -> None:
    """A possessive move with no target is not understood. The token does not move."""
    campaign_id, session_id = table
    spoken = gateway.post(
        SPEAK_PATH,
        json=_speech(session_id, campaign_id, "move my warrior"),
        headers=bearer(DM),
    )

    assert spoken.status_code == 200, spoken.text
    assert spoken.json()["action_type"] == "narrative"
    board = httpx.get(f"{board_state_upstream}/api/v1/boards/{session_id}", headers=bearer(DM))
    assert board.json()["tokens"][VALEROS]["x"] == VALEROS_START[0]
