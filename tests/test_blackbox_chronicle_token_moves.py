"""Blackbox frontdoor tests: a token move appears in the session chronicle feed.

board_state publishes `TokenMoved` on `runefoble.events.board`. The game_session consumer
records one `TokenMoveChronicled` event on the session, and the feed
(`GET /api/v1/sessions/{id}/events`) shows "<token> moved to (x, y)". Setup uses the public
campaign, session and board routes, or the standard `TokenMoved` event on the public stream.
Redis is the only double (MockAsyncRedis). Governed by ADR-0006, ADR-0011, ADR-0015 and Hard
Invariant 7.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Generator
from typing import Any
from uuid import UUID, uuid4

import pytest
import redis.asyncio
from board_state.main import app as board_app
from fastapi.testclient import TestClient
from runefoble_events.events import TokenMoved, TokenPlaced
from runefoble_platform.redis_bus import RedisStreamsEventBus

from tests.helpers.game_session_app import session_app
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.polling import wait_until
from tests.helpers.ws_identity import SIGNING_ISSUER

BOARD_STREAM = "runefoble.events.board"
BOARD_DLQ = f"{BOARD_STREAM}.dlq"
SESSION_STREAM = "runefoble.events.session"
CHRONICLED_EVENT = "runefoble.events.session.token_move_chronicled"
DM = "dm-evelyn"

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.fixture
def stream_redis(mock_bus, monkeypatch: pytest.MonkeyPatch) -> MockAsyncRedis:
    """One Redis double for every publisher and the game_session lifespan consumers."""
    monkeypatch.setattr(redis.asyncio, "from_url", lambda *_args, **_kwargs: mock_bus)
    return mock_bus


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(DM)}"}


@pytest.fixture
def client(stream_redis: MockAsyncRedis) -> Generator[TestClient]:
    """Run the real game_session lifespan, so the board consumer starts and reads the stream."""
    with TestClient(session_app, headers=_headers()) as test_client:
        assert test_client.get("/healthz").json()["consumers"] == {"game_session": "running"}
        yield test_client


def _create(client: TestClient) -> tuple[str, str]:
    """Create a campaign and a session in it through public routes. Return both ids."""
    campaign = client.post("/api/v1/campaigns", json={"title": "Tomb"})
    assert campaign.status_code == 201, campaign.text
    campaign_id = campaign.json()["id"]
    res = client.post(f"/api/v1/campaigns/{campaign_id}/sessions", json={"title": "Crypt"})
    assert res.status_code == 201, res.text
    return campaign_id, res.json()["id"]


def _moved(session_id: str, *, name: str = "Valeros the Bold", to: tuple[int, int] = (3, 3)):
    return TokenMoved(
        aggregate_id=UUID(session_id),
        session_id=UUID(session_id),
        token_id="tok-valeros",
        name=name,
        from_x=1,
        from_y=1,
        to_x=to[0],
        to_y=to[1],
    )


def _publish(stream_redis: MockAsyncRedis, event: Any) -> None:
    async def _send() -> None:
        await RedisStreamsEventBus(client=stream_redis).publish_event(BOARD_STREAM, event)

    asyncio.run(_send())


def _move_lines(client: TestClient, session_id: str) -> list[dict[str, Any]]:
    feed = client.get(f"/api/v1/sessions/{session_id}/events")
    assert feed.status_code == 200, feed.text
    return [entry for entry in feed.json() if entry["kind"] == "token_moved"]


def _chronicled(stream_redis: MockAsyncRedis, session_id: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for _entry_id, fields in stream_redis.streams.get(SESSION_STREAM, []):
        payload = json.loads(fields["payload"])
        if fields["event_type"] == CHRONICLED_EVENT and str(payload["session_id"]) == session_id:
            events.append(payload)
    return events


def test_a_board_route_move_shows_in_the_session_chronicle(client, stream_redis) -> None:
    campaign_id, session_id = _create(client)
    with TestClient(board_app, headers=_headers()) as board:
        created = board.post(
            "/api/v1/boards",
            json={"campaign_id": campaign_id, "session_id": session_id, "cols": 8, "rows": 8},
        )
        assert created.status_code == 200, created.text
        placed = board.post(
            f"/api/v1/boards/{session_id}/tokens",
            json={"token_id": "tok-valeros", "name": "Valeros the Bold", "x": 1, "y": 1},
        )
        assert placed.status_code == 200, placed.text
        moved = board.post(
            f"/api/v1/boards/{session_id}/tokens/tok-valeros/move", json={"to_x": 3, "to_y": 3}
        )
        assert moved.status_code == 200, moved.text

    assert wait_until(
        lambda: bool(_move_lines(client, session_id)), timeout_s=10.0, interval_s=0.05
    )
    (line,) = _move_lines(client, session_id)
    assert line["speaker"] == "Valeros the Bold"
    assert line["text"] == "Valeros the Bold moved to (3, 3)"
    assert line["action_type"] == "board_move"
    (event,) = _chronicled(stream_redis, session_id)
    assert event["event_id"] == line["event_id"]


def test_a_redelivered_move_records_one_chronicle_line(client, stream_redis) -> None:
    _campaign_id, session_id = _create(client)
    move = _moved(session_id)
    _publish(stream_redis, move)
    _publish(stream_redis, move)  # the redelivery
    # A later move is a barrier: the consumer reads the stream in order.
    _publish(stream_redis, _moved(session_id, to=(5, 2)))

    assert wait_until(
        lambda: len(_move_lines(client, session_id)) >= 2, timeout_s=10.0, interval_s=0.05
    )
    texts = [line["text"] for line in _move_lines(client, session_id)]
    assert texts == ["Valeros the Bold moved to (3, 3)", "Valeros the Bold moved to (5, 2)"]
    assert len(_chronicled(stream_redis, session_id)) == 2
    assert stream_redis.streams.get(BOARD_DLQ, []) == []


def test_other_board_events_add_no_chronicle_line(client, stream_redis) -> None:
    _campaign_id, session_id = _create(client)
    _publish(
        stream_redis,
        TokenPlaced(
            aggregate_id=UUID(session_id),
            session_id=UUID(session_id),
            name="Goblin",
            token_type="monster",
            x=2,
            y=2,
        ),
    )
    _publish(stream_redis, _moved(session_id, name="Kyra"))

    assert wait_until(
        lambda: bool(_move_lines(client, session_id)), timeout_s=10.0, interval_s=0.05
    )
    assert [line["text"] for line in _move_lines(client, session_id)] == ["Kyra moved to (3, 3)"]
    assert stream_redis.streams.get(BOARD_DLQ, []) == []


def test_a_move_for_an_unknown_session_is_dead_lettered(client, stream_redis) -> None:
    unknown = str(uuid4())
    _publish(stream_redis, _moved(unknown))

    assert wait_until(
        lambda: bool(stream_redis.streams.get(BOARD_DLQ)), timeout_s=10.0, interval_s=0.05
    )
    (_entry_id, dead_letter), *_ = stream_redis.streams[BOARD_DLQ]
    assert unknown in dead_letter["error_reason"]
    assert _chronicled(stream_redis, unknown) == []
