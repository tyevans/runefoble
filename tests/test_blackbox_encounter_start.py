"""Blackbox tests: one owner route starts combat and places enemy tokens (TASK-0749).

game_session starts combat through POST /api/v1/sessions/{id}/encounters/start. board_state
consumes the combat start from the session stream and places the tokens. Redis is an external
process. Every service publish goes to the shared in-memory bus, and both services read it.
Setup and assertions use public HTTP routes and the stream the services publish to.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import httpx
import pytest
import redis.asyncio

from tests.helpers.game_session_setup import start_session_with_player
from tests.helpers.live_services import serve
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.polling import wait_until
from tests.helpers.ws_identity import SIGNING_ISSUER, bearer

pytestmark = pytest.mark.usefixtures("board_campaign")

SESSION_STREAM = "runefoble.events.session"
GROUP = "board_state_encounter_workers"
START_TYPE = "runefoble.events.session.combat_encounter_started"
DEAD_LETTER_STREAM = f"{SESSION_STREAM}.dlq"


@pytest.fixture
def mock_redis(monkeypatch: pytest.MonkeyPatch, mock_bus: MockAsyncRedis) -> MockAsyncRedis:
    """Give the board_state lifespan the same in-memory Redis the services publish to."""
    monkeypatch.setattr(redis.asyncio, "from_url", lambda *_a, **_k: mock_bus)
    return mock_bus


@pytest.fixture
def upstreams(mock_redis: MockAsyncRedis) -> Iterator[dict[str, str]]:
    """Run game_session and board_state as HTTP services. board_state starts its consumers."""
    from board_state.main import app as board_app
    from game_session.main import app as session_app
    from game_session.settlement.auth.tokens import (
        get_zitadel_auth_service,
        set_zitadel_auth_service,
    )

    previous = get_zitadel_auth_service()
    set_zitadel_auth_service(SIGNING_ISSUER.verifier())
    try:
        with serve(board_app, lifespan="on") as board_url, serve(session_app) as session_url:
            yield {"board": board_url, "session": session_url}
    finally:
        set_zitadel_auth_service(previous)


def _start_body(enemies: list[dict[str, Any]]) -> dict[str, Any]:
    return {"enemies": enemies}


def _enemy(name: str, x: int, y: int) -> dict[str, Any]:
    return {"name": name, "x": x, "y": y, "hp": 7, "cr": 0.25}


def _start_encounter(
    session_url: str, session_id: str, enemies: list[dict[str, Any]]
) -> httpx.Response:
    with httpx.Client(base_url=session_url, headers=bearer("user-test")) as http:
        return http.post(
            f"/api/v1/sessions/{session_id}/encounters/start", json=_start_body(enemies)
        )


def _combat(session_url: str, session_id: str) -> dict[str, Any]:
    with httpx.Client(base_url=session_url, headers=bearer("user-test")) as http:
        response = http.get(f"/api/v1/sessions/{session_id}/combat")
        assert response.status_code == 200, response.text
        return response.json()


def _board_tokens(board_url: str, session_id: str) -> list[dict[str, Any]] | None:
    with httpx.Client(base_url=board_url, headers=bearer("user-test")) as http:
        response = http.get(f"/api/v1/boards/{session_id}")
        if response.status_code == 404:
            return None
        assert response.status_code == 200, response.text
        return list(response.json()["tokens"].values())


def _group_caught_up(mock_redis: MockAsyncRedis) -> bool:
    entries = mock_redis.streams.get(SESSION_STREAM, [])
    group = mock_redis.groups.get((SESSION_STREAM, GROUP))
    return group is not None and group["delivered_idx"] >= len(entries) and not group["pending"]


def test_start_answers_200_then_board_gets_every_token(
    upstreams: dict[str, str], mock_redis: MockAsyncRedis
) -> None:
    """The start answers 200 with combat started. After the consumer runs, the board has each token."""
    session_id = start_session_with_player(upstreams["session"])

    response = _start_encounter(
        upstreams["session"], session_id, [_enemy("Goblin", 1, 1), _enemy("Orc", 3, 2)]
    )

    assert response.status_code == 200, response.text
    assert response.json()["in_combat"] is True
    assert _combat(upstreams["session"], session_id)["in_combat"] is True
    wait_until(
        lambda: _board_tokens(upstreams["board"], session_id) not in (None, []),
        timeout_s=5.0,
    )
    tokens = _board_tokens(upstreams["board"], session_id) or []
    assert sorted((t["name"], t["x"], t["y"], t["token_type"]) for t in tokens) == [
        ("Goblin", 1, 1, "monster"),
        ("Orc", 3, 2, "monster"),
    ]


def test_off_grid_placement_is_dead_lettered_and_combat_stays(
    upstreams: dict[str, str], mock_redis: MockAsyncRedis
) -> None:
    """A placement off the grid dead-letters the start. Combat stays started and no token lands."""
    session_id = start_session_with_player(upstreams["session"])

    response = _start_encounter(
        upstreams["session"], session_id, [_enemy("Goblin", 1, 1), _enemy("Ogre", 50, 50)]
    )

    assert response.status_code == 200, response.text
    wait_until(
        lambda: bool(mock_redis.streams.get(DEAD_LETTER_STREAM)),
        timeout_s=5.0,
    )
    assert _combat(upstreams["session"], session_id)["in_combat"] is True
    assert not _board_tokens(upstreams["board"], session_id)


def test_occupied_cell_is_dead_lettered_and_combat_stays(
    upstreams: dict[str, str], mock_redis: MockAsyncRedis
) -> None:
    """Two enemies on one cell dead-letter the start. Combat stays started and no token lands."""
    session_id = start_session_with_player(upstreams["session"])

    response = _start_encounter(
        upstreams["session"], session_id, [_enemy("Goblin", 2, 2), _enemy("Orc", 2, 2)]
    )

    assert response.status_code == 200, response.text
    wait_until(
        lambda: bool(mock_redis.streams.get(DEAD_LETTER_STREAM)),
        timeout_s=5.0,
    )
    assert _combat(upstreams["session"], session_id)["in_combat"] is True
    assert not _board_tokens(upstreams["board"], session_id)


def test_redelivered_start_places_nothing_twice(
    upstreams: dict[str, str], mock_redis: MockAsyncRedis
) -> None:
    """Redelivering the same combat start event leaves each token placed once."""
    session_id = start_session_with_player(upstreams["session"])
    _start_encounter(upstreams["session"], session_id, [_enemy("Goblin", 4, 4)])
    wait_until(
        lambda: len(_board_tokens(upstreams["board"], session_id) or []) == 1,
        timeout_s=5.0,
    )
    start_entries = [
        (entry_id, fields)
        for entry_id, fields in mock_redis.streams[SESSION_STREAM]
        if START_TYPE in str(fields)
    ]
    assert len(start_entries) == 1
    _, fields = start_entries[0]
    mock_redis.streams[SESSION_STREAM].append(("1700000000999-1", fields))

    wait_until(lambda: _group_caught_up(mock_redis), timeout_s=5.0)

    tokens = _board_tokens(upstreams["board"], session_id) or []
    assert [(t["name"], t["x"], t["y"]) for t in tokens] == [("Goblin", 4, 4)]
    # The redelivery is skipped, not refused. A refusal would dead-letter it on the occupied cell.
    assert not mock_redis.streams.get(DEAD_LETTER_STREAM)


def test_player_without_control_gets_403(upstreams: dict[str, str]) -> None:
    """A caller who lacks session control cannot start an encounter."""
    session_id = start_session_with_player(upstreams["session"])
    with httpx.Client(base_url=upstreams["session"], headers=bearer(f"stranger-{uuid4()}")) as http:
        response = http.post(
            f"/api/v1/sessions/{session_id}/encounters/start",
            json=_start_body([_enemy("Goblin", 1, 1)]),
        )
    assert response.status_code == 403, response.text
