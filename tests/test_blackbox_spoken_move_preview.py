"""Blackbox chain test: a spoken move reaches the board only through preview and player confirm (TASK-0814).

Governed by the design rule "The Watcher proposes; only the player's `confirm_move` commits a
board move" (AGENTS.md, ADR-0015). The chain runs through public frontdoors: the gateway
speak-and-act route, the live The Watcher and board_state upstreams, and the board WebSocket.
The board socket enters the in-process `board_state` app through the TestClient. Setup uses
public routes only (ADR-0014, Hard Invariant 7).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import httpx
import pytest
from board_state.main import app as board_app
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from inference_worker import api as worker_api
from inference_worker.llm_factory import build_llm_port
from runefoble_events.events import TokenMoved
from runefoble_platform.event_deserializer import deserialize_event

from tests.helpers.fake_openai_server import FakeOpenAI
from tests.helpers.inference_worker_port import install_worker_port
from tests.helpers.live_services import closed_port_url, serve
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.spectator_table import open_board_table
from tests.helpers.the_watcher_app import watcher_app
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


def _speech(session_id: str, campaign_id: str, **changes: object) -> dict[str, object]:
    body: dict[str, object] = {
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
    body.update(changes)
    return body


def _position(board_url: str, session_id: str, token_id: str = GOBLIN) -> tuple[int, int]:
    board = httpx.get(f"{board_url}/api/v1/boards/{session_id}", headers=bearer(DM))
    assert board.status_code == 200, board.text
    token = board.json()["tokens"][token_id]
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


def _committed_moves(mock_bus: MockAsyncRedis, token_id: str) -> list[TokenMoved]:
    """Return the TokenMoved events for one token that reached the board stream."""
    entries = mock_bus.streams.get("runefoble.events.board", [])
    events = [deserialize_event(fields) for _id, fields in entries]
    return [e for e in events if isinstance(e, TokenMoved) and e.token_id == token_id]


def test_confirmed_spoken_move_publishes_one_token_moved_and_the_proposal_publishes_none(
    gateway: TestClient,
    table: tuple[str, str],
    board_socket: TestClient,
    mock_bus: MockAsyncRedis,
) -> None:
    """Analytics reads the board stream. A proposal adds nothing. The confirm adds one move."""
    campaign_id, session_id = table

    with board_socket.websocket_connect(
        f"/ws/boards/{session_id}", subprotocols=ws_subprotocols(DM)
    ) as ws:
        ws.receive_json()
        spoken = gateway.post(SPEAK_PATH, json=_speech(session_id, campaign_id), headers=bearer(DM))
        assert spoken.status_code == 200, spoken.text
        assert ws.receive_json()["type"] == "ghost_preview"
        assert _committed_moves(mock_bus, GOBLIN) == []

        ws.send_json({"action": "confirm_move", "token_id": GOBLIN, "to_x": 4, "to_y": 2})
        assert ws.receive_json()["type"] == "token_moved"

    moves = _committed_moves(mock_bus, GOBLIN)
    assert len(moves) == 1
    assert (moves[0].from_x, moves[0].from_y) == GOBLIN_START
    assert (moves[0].to_x, moves[0].to_y) == GOBLIN_TARGET


# Destination rules (TASK-0942). The Valeros token (`t1`) starts at (2, 3). The goblin stands at
# (6, 2). Its free neighbours in the 8 x 8 grid are the cells around it. The nearest one to
# (2, 3), by grid distance, is (5, 1). Ties go to the lower `y`, then the lower `x`.
VALEROS = "t1"
VALEROS_START = (2, 3)
GOBLIN_NAME_SPEECH = "move to the goblin stalker"


def _move_from(
    session_id: str, campaign_id: str, token_id: str, origin: tuple[int, int], transcript: str
) -> dict[str, object]:
    """A speech body for a move by `token_id` from `origin`, with the speaker named by the token."""
    names = {VALEROS: "Valeros", GOBLIN: "Goblin Stalker"}
    return _speech(
        session_id,
        campaign_id,
        token_id=token_id,
        speaker_name=names[token_id],
        from_x=origin[0],
        from_y=origin[1],
        transcript=transcript,
    )


def _place_token(board_url: str, session_id: str, token_id: str, name: str, x: int, y: int) -> None:
    """Place one token on the board through the public board route."""
    placed = httpx.post(
        f"{board_url}/api/v1/boards/{session_id}/tokens",
        json={"token_id": token_id, "name": name, "token_type": "npc", "x": x, "y": y, "hp": 5},
        headers=bearer(DM),
    )
    assert placed.status_code == 200, placed.text


def _expect_next_frame_is_staged(
    gateway: TestClient, ws: Any, campaign_id: str, session_id: str, to: tuple[int, int]
) -> None:
    """A rejected proposal sends no frame. The next frame must answer a later valid move."""
    spoken = gateway.post(SPEAK_PATH, json=_speech(session_id, campaign_id), headers=bearer(DM))
    assert spoken.status_code == 200, spoken.text
    frame = ws.receive_json()
    assert frame["type"] == "ghost_preview"
    assert (frame["preview"]["to_x"], frame["preview"]["to_y"]) == to


def test_named_target_stages_the_free_neighbour_nearest_the_origin(
    gateway: TestClient,
    table: tuple[str, str],
    board_state_upstream: str,
    board_socket: TestClient,
) -> None:
    """A move to a named token stages a free cell next to it. The token does not move yet."""
    campaign_id, session_id = table

    with board_socket.websocket_connect(
        f"/ws/boards/{session_id}", subprotocols=ws_subprotocols(DM)
    ) as ws:
        ws.receive_json()
        body = _move_from(session_id, campaign_id, VALEROS, VALEROS_START, GOBLIN_NAME_SPEECH)
        spoken = gateway.post(SPEAK_PATH, json=body, headers=bearer(DM))
        assert spoken.status_code == 200, spoken.text

        preview = ws.receive_json()

    assert preview["type"] == "ghost_preview"
    assert preview["preview"]["token_id"] == VALEROS
    assert (preview["preview"]["to_x"], preview["preview"]["to_y"]) == (5, 1)
    assert _position(board_state_upstream, session_id, VALEROS) == VALEROS_START


def test_named_target_skips_a_neighbour_that_another_token_holds(
    gateway: TestClient,
    table: tuple[str, str],
    board_state_upstream: str,
    board_socket: TestClient,
) -> None:
    """A neighbour held by a token is not free. The next nearest free neighbour is staged."""
    campaign_id, session_id = table
    _place_token(board_state_upstream, session_id, "t_blocker", "Blocker", 5, 1)

    with board_socket.websocket_connect(
        f"/ws/boards/{session_id}", subprotocols=ws_subprotocols(DM)
    ) as ws:
        ws.receive_json()
        body = _move_from(session_id, campaign_id, VALEROS, VALEROS_START, GOBLIN_NAME_SPEECH)
        assert gateway.post(SPEAK_PATH, json=body, headers=bearer(DM)).status_code == 200

        preview = ws.receive_json()

    assert (preview["preview"]["to_x"], preview["preview"]["to_y"]) == (5, 2)


def test_coordinate_move_with_grammar_keys_stages_the_given_cell(
    gateway: TestClient,
    table: tuple[str, str],
    board_socket: TestClient,
) -> None:
    """The grammar sets `to_x` and `to_y`. The preview goes to that cell."""
    campaign_id, session_id = table
    body = _move_from(session_id, campaign_id, VALEROS, VALEROS_START, "move to 4, 7")

    with board_socket.websocket_connect(
        f"/ws/boards/{session_id}", subprotocols=ws_subprotocols(DM)
    ) as ws:
        ws.receive_json()
        assert gateway.post(SPEAK_PATH, json=body, headers=bearer(DM)).status_code == 200
        preview = ws.receive_json()

    assert (preview["preview"]["to_x"], preview["preview"]["to_y"]) == (4, 7)


def test_coordinate_outside_the_grid_is_a_client_error_and_stages_nothing(
    gateway: TestClient,
    table: tuple[str, str],
    board_socket: TestClient,
) -> None:
    """A destination outside the 8 x 8 grid returns 422. No preview reaches the board socket."""
    campaign_id, session_id = table
    body = _move_from(session_id, campaign_id, VALEROS, VALEROS_START, "move to 9, 9")

    with board_socket.websocket_connect(
        f"/ws/boards/{session_id}", subprotocols=ws_subprotocols(DM)
    ) as ws:
        ws.receive_json()
        spoken = gateway.post(SPEAK_PATH, json=body, headers=bearer(DM))
        assert spoken.status_code == 422, spoken.text
        _expect_next_frame_is_staged(gateway, ws, campaign_id, session_id, to=(4, 2))


def test_missing_origin_is_a_client_error_and_stages_nothing(
    gateway: TestClient,
    table: tuple[str, str],
    board_state_upstream: str,
    board_socket: TestClient,
) -> None:
    """Without `from_x` the Watcher does not invent an origin. It answers 422 and sends no frame."""
    campaign_id, session_id = table
    body = _speech(session_id, campaign_id)
    del body["from_x"]

    with board_socket.websocket_connect(
        f"/ws/boards/{session_id}", subprotocols=ws_subprotocols(DM)
    ) as ws:
        ws.receive_json()
        spoken = gateway.post(SPEAK_PATH, json=body, headers=bearer(DM))
        assert spoken.status_code == 422, spoken.text
        assert "from_x" in spoken.text
        _expect_next_frame_is_staged(gateway, ws, campaign_id, session_id, to=(4, 2))

    assert _position(board_state_upstream, session_id) == GOBLIN_START


def test_unknown_target_name_is_a_client_error_and_stages_nothing(
    gateway: TestClient,
    table: tuple[str, str],
    board_socket: TestClient,
) -> None:
    """A name that no token on the board carries returns 422. No preview is staged."""
    campaign_id, session_id = table
    body = _move_from(session_id, campaign_id, VALEROS, VALEROS_START, "move to the dragon")

    with board_socket.websocket_connect(
        f"/ws/boards/{session_id}", subprotocols=ws_subprotocols(DM)
    ) as ws:
        ws.receive_json()
        spoken = gateway.post(SPEAK_PATH, json=body, headers=bearer(DM))
        assert spoken.status_code == 422, spoken.text
        _expect_next_frame_is_staged(gateway, ws, campaign_id, session_id, to=(4, 2))


def test_duplicate_target_name_is_a_conflict_and_stages_nothing(
    gateway: TestClient,
    table: tuple[str, str],
    board_state_upstream: str,
    board_socket: TestClient,
) -> None:
    """Two tokens named alike make the target ambiguous. The Watcher answers 409."""
    campaign_id, session_id = table
    _place_token(board_state_upstream, session_id, "t_goblin_2", "Goblin Stalker", 0, 7)
    body = _move_from(session_id, campaign_id, VALEROS, VALEROS_START, GOBLIN_NAME_SPEECH)

    with board_socket.websocket_connect(
        f"/ws/boards/{session_id}", subprotocols=ws_subprotocols(DM)
    ) as ws:
        ws.receive_json()
        spoken = gateway.post(SPEAK_PATH, json=body, headers=bearer(DM))
        assert spoken.status_code == 409, spoken.text
        _expect_next_frame_is_staged(gateway, ws, campaign_id, session_id, to=(4, 2))


def test_target_without_a_free_neighbour_is_a_conflict_and_stages_nothing(
    gateway: TestClient,
    table: tuple[str, str],
    board_state_upstream: str,
    board_socket: TestClient,
) -> None:
    """All eight neighbours of the goblin are held. The Watcher answers 409 and stages nothing."""
    campaign_id, session_id = table
    ring = [(5, 1), (6, 1), (7, 1), (5, 2), (7, 2), (5, 3), (6, 3), (7, 3)]
    for index, (x, y) in enumerate(ring):
        _place_token(board_state_upstream, session_id, f"t_ring_{index}", "Ring", x, y)
    body = _move_from(session_id, campaign_id, VALEROS, VALEROS_START, GOBLIN_NAME_SPEECH)

    with board_socket.websocket_connect(
        f"/ws/boards/{session_id}", subprotocols=ws_subprotocols(DM)
    ) as ws:
        ws.receive_json()
        spoken = gateway.post(SPEAK_PATH, json=body, headers=bearer(DM))
        assert spoken.status_code == 409, spoken.text
        _expect_next_frame_is_staged(gateway, ws, campaign_id, session_id, to=(4, 2))


NARRATIVE_MOVE_SPEECH = "I sneak toward the goblin"


@pytest.fixture
def worker_loopback(monkeypatch: pytest.MonkeyPatch, fake_llm: FakeOpenAI) -> Iterator[str]:
    """The real inference worker app, served on loopback. Only the model runtime is a fake.

    The grammar returns the speech as `narrative`, so the intent port sends it to the worker
    (ADR-0022 b). The fake model answers a move to cell (4, 7).
    """
    fake_llm.content = json.dumps(
        {
            "action_type": "move",
            "narrative_flavor": "The goblin slips.",
            "target_x": 4,
            "target_y": 7,
        }
    )
    install_worker_port(monkeypatch, build_llm_port(fake_llm.settings()))
    with serve(worker_api.app) as url:
        monkeypatch.setenv("RUNEFOBLE_WATCHER_INTENT_ENGINE", "inference_worker")
        monkeypatch.setenv("RUNEFOBLE_INFERENCE_URL", url)
        yield url


def test_narrative_speech_answered_by_the_worker_stages_the_worker_target(
    gateway: TestClient,
    table: tuple[str, str],
    worker_loopback: str,
    board_socket: TestClient,
) -> None:
    """The grammar sends the speech to the worker. The worker's target cell is the preview."""
    campaign_id, session_id = table
    body = _move_from(session_id, campaign_id, VALEROS, VALEROS_START, NARRATIVE_MOVE_SPEECH)

    with board_socket.websocket_connect(
        f"/ws/boards/{session_id}", subprotocols=ws_subprotocols(DM)
    ) as ws:
        ws.receive_json()
        spoken = gateway.post(SPEAK_PATH, json=body, headers=bearer(DM))
        assert spoken.status_code == 200, spoken.text
        preview = ws.receive_json()

    assert (preview["preview"]["to_x"], preview["preview"]["to_y"]) == (4, 7)
