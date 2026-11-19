"""Blackbox frontdoor tests: an approved audience item drop places a loot token (TASK-0837).

Setup uses the public campaign, board and token routes. The modifier is published as the
standard `AudienceModifierApproved` event on `runefoble.events.audience`. The result is read
through the public board read and the spectator view. Redis is the only double (MockAsyncRedis).
The board_state consumers start through the real lifespan. Governed by ADR-0006, ADR-0007,
and ADR-0015.
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import uuid4

import pytest
import redis.asyncio
from board_state.main import app as board_app
from fastapi.testclient import TestClient
from runefoble_events.events import AudienceModifierApproved
from runefoble_platform.redis_bus import RedisStreamsEventBus

from tests.helpers.campaign_setup import create_dm_campaign
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.polling import wait_until
from tests.helpers.ws_identity import bearer

AUDIENCE_STREAM = "runefoble.events.audience"
AUDIENCE_DLQ = f"{AUDIENCE_STREAM}.dlq"

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.fixture
def shared_redis(mock_bus: MockAsyncRedis, monkeypatch: pytest.MonkeyPatch) -> MockAsyncRedis:
    """One Redis double for the publisher and the board_state lifespan consumers."""
    monkeypatch.setattr(redis.asyncio, "from_url", lambda *_args, **_kwargs: mock_bus)
    return mock_bus


def _create_board(client: TestClient, campaign_id: str, session_id: str) -> None:
    res = client.post(
        "/api/v1/boards",
        json={"campaign_id": campaign_id, "session_id": session_id, "cols": 16, "rows": 16},
    )
    assert res.status_code == 200, res.text


def _place_pc(client: TestClient, session_id: str, token_id: str, x: int, y: int) -> None:
    res = client.post(
        f"/api/v1/boards/{session_id}/tokens",
        json={"token_id": token_id, "name": "Ash", "token_type": "pc", "x": x, "y": y},
    )
    assert res.status_code == 200, res.text


def _modifier(
    campaign_id: str,
    session_id: str,
    *,
    proposal_id: Any = None,
    approved: bool = True,
    modifier_type: str = "item_drop",
    parameters: dict[str, Any] | None = None,
) -> AudienceModifierApproved:
    return AudienceModifierApproved(
        proposal_id=proposal_id or uuid4(),
        poll_id=uuid4(),
        campaign_id=campaign_id,
        session_id=session_id,
        approved_by="user-test",
        approved=approved,
        modifier_type=modifier_type,
        parameters=parameters
        if parameters is not None
        else {"x": 2, "y": 3, "item_name": "Healing Potion"},
    )


def _publish(stream_redis: MockAsyncRedis, event: AudienceModifierApproved) -> None:
    async def _send() -> None:
        await RedisStreamsEventBus(client=stream_redis).publish_event(AUDIENCE_STREAM, event)

    asyncio.run(_send())


def _tokens(client: TestClient, session_id: str) -> dict[str, dict[str, Any]]:
    board = client.get(f"/api/v1/boards/{session_id}").json()
    return board["tokens"]


def _loot_at(client: TestClient, session_id: str, x: int, y: int) -> dict[str, Any] | None:
    for token in _tokens(client, session_id).values():
        if token["token_type"] == "loot" and (token["x"], token["y"]) == (x, y):
            return token
    return None


def _loot_count(client: TestClient, session_id: str) -> int:
    return sum(1 for t in _tokens(client, session_id).values() if t["token_type"] == "loot")


def test_approved_item_drop_places_a_loot_token_with_the_item_name(shared_redis: MockAsyncRedis):
    campaign_id = create_dm_campaign("user-test")
    session_id = f"sess-{uuid4().hex[:8]}"
    proposal_id = uuid4()

    with TestClient(board_app, headers=bearer("user-test")) as client:
        assert client.get("/healthz").json()["consumers"] == {"board_state": "running"}
        _create_board(client, campaign_id, session_id)
        _publish(shared_redis, _modifier(campaign_id, session_id, proposal_id=proposal_id))

        assert wait_until(
            lambda: _loot_at(client, session_id, 2, 3) is not None,
            timeout_s=10.0,
            interval_s=0.05,
        )
        token = _loot_at(client, session_id, 2, 3)
        assert token is not None
        assert token["name"] == "Healing Potion"
        assert token["token_id"] == str(proposal_id)
        assert token["is_friendly"] is False
        assert shared_redis.streams.get(AUDIENCE_DLQ, []) == []

        spectator = client.get(f"/api/v1/boards/{session_id}/spectator").json()
        assert any(
            spec["token_type"] == "loot"
            and spec["name"] == "Healing Potion"
            and (spec["x"], spec["y"]) == (2, 3)
            for spec in spectator["tokens"]
        )


def test_redelivered_item_drop_places_one_loot_token(shared_redis: MockAsyncRedis):
    """The same proposal delivered twice leaves one loot token. A later drop is a barrier."""
    campaign_id = create_dm_campaign("user-test")
    session_id = f"sess-{uuid4().hex[:8]}"
    proposal_id = uuid4()

    with TestClient(board_app, headers=bearer("user-test")) as client:
        _create_board(client, campaign_id, session_id)
        first = _modifier(campaign_id, session_id, proposal_id=proposal_id)
        _publish(shared_redis, first)
        _publish(shared_redis, first)
        _publish(
            shared_redis,
            _modifier(campaign_id, session_id, parameters={"x": 5, "y": 5, "item_name": "Rope"}),
        )

        assert wait_until(
            lambda: _loot_at(client, session_id, 5, 5) is not None,
            timeout_s=10.0,
            interval_s=0.05,
        )
        assert _loot_count(client, session_id) == 2
        assert shared_redis.streams.get(AUDIENCE_DLQ, []) == []


def test_vetoed_item_drop_and_other_modifier_types_change_nothing(shared_redis: MockAsyncRedis):
    campaign_id = create_dm_campaign("user-test")
    session_id = f"sess-{uuid4().hex[:8]}"

    with TestClient(board_app, headers=bearer("user-test")) as client:
        _create_board(client, campaign_id, session_id)
        _publish(shared_redis, _modifier(campaign_id, session_id, approved=False))
        _publish(
            shared_redis,
            _modifier(
                campaign_id,
                session_id,
                modifier_type="hazard_spawn",
                parameters={"x": 4, "y": 4, "item_name": "Rope", "hazard_type": "fire"},
            ),
        )
        # A later approved drop is a barrier: the consumer reads the stream in order.
        _publish(
            shared_redis,
            _modifier(campaign_id, session_id, parameters={"x": 6, "y": 6, "item_name": "Map"}),
        )

        assert wait_until(
            lambda: _loot_at(client, session_id, 6, 6) is not None,
            timeout_s=10.0,
            interval_s=0.05,
        )
        assert _loot_at(client, session_id, 2, 3) is None
        assert _loot_at(client, session_id, 4, 4) is None
        assert _tokens(client, session_id).keys() == {
            _loot_at(client, session_id, 6, 6)["token_id"]
        }
        assert shared_redis.streams.get(AUDIENCE_DLQ, []) == []


@pytest.mark.parametrize(
    ("parameters", "expected_reason"),
    [
        ({"x": 20, "y": 3, "item_name": "Rope"}, "out of grid bounds"),
        ({"x": 2, "y": 3, "item_name": "   "}, "'item_name'"),
        ({"y": 3, "item_name": "Rope"}, "'x'"),
        ({"x": "2", "y": 3, "item_name": "Rope"}, "integer 'x'"),
        ({"x": 2, "y": 3, "item_name": "Rope", "item_id": 7}, "text 'item_id'"),
    ],
    ids=["off_grid", "blank_item_name", "missing_x", "text_x", "non_text_item_id"],
)
def test_invalid_item_drop_is_dead_lettered_and_changes_nothing(
    shared_redis: MockAsyncRedis, parameters: dict[str, Any], expected_reason: str
):
    campaign_id = create_dm_campaign("user-test")
    session_id = f"sess-{uuid4().hex[:8]}"

    with TestClient(board_app, headers=bearer("user-test")) as client:
        _create_board(client, campaign_id, session_id)
        _publish(shared_redis, _modifier(campaign_id, session_id, parameters=parameters))

        assert wait_until(
            lambda: bool(shared_redis.streams.get(AUDIENCE_DLQ)), timeout_s=10.0, interval_s=0.05
        )
        (_entry_id, dead_letter), *_ = shared_redis.streams[AUDIENCE_DLQ]
        assert expected_reason in dead_letter["error_reason"]
        assert _tokens(client, session_id) == {}


def test_item_drop_on_an_occupied_cell_is_dead_lettered(shared_redis: MockAsyncRedis):
    campaign_id = create_dm_campaign("user-test")
    session_id = f"sess-{uuid4().hex[:8]}"

    with TestClient(board_app, headers=bearer("user-test")) as client:
        _create_board(client, campaign_id, session_id)
        _place_pc(client, session_id, "pc-ash", 2, 3)
        _publish(shared_redis, _modifier(campaign_id, session_id))

        assert wait_until(
            lambda: bool(shared_redis.streams.get(AUDIENCE_DLQ)), timeout_s=10.0, interval_s=0.05
        )
        (_entry_id, dead_letter), *_ = shared_redis.streams[AUDIENCE_DLQ]
        assert "already holds a token" in dead_letter["error_reason"]
        assert list(_tokens(client, session_id)) == ["pc-ash"]


def test_item_drop_for_another_campaign_is_dead_lettered(shared_redis: MockAsyncRedis):
    """The modifier names a campaign that does not own the board. The board is unchanged."""
    board_owner = create_dm_campaign("user-test")
    other_campaign = create_dm_campaign("user-test")
    session_id = f"sess-{uuid4().hex[:8]}"

    with TestClient(board_app, headers=bearer("user-test")) as client:
        _create_board(client, board_owner, session_id)
        _publish(shared_redis, _modifier(other_campaign, session_id))

        assert wait_until(
            lambda: bool(shared_redis.streams.get(AUDIENCE_DLQ)), timeout_s=10.0, interval_s=0.05
        )
        (_entry_id, dead_letter), *_ = shared_redis.streams[AUDIENCE_DLQ]
        assert "belongs to campaign" in dead_letter["error_reason"]
        assert _tokens(client, session_id) == {}


def test_token_can_move_onto_a_loot_cell(shared_redis: MockAsyncRedis):
    """A loot token does not block movement. A player token walks onto its cell."""
    campaign_id = create_dm_campaign("user-test")
    session_id = f"sess-{uuid4().hex[:8]}"

    with TestClient(board_app, headers=bearer("user-test")) as client:
        _create_board(client, campaign_id, session_id)
        _place_pc(client, session_id, "pc-ash", 1, 1)
        _publish(
            shared_redis,
            _modifier(campaign_id, session_id, parameters={"x": 2, "y": 2, "item_name": "Rope"}),
        )

        assert wait_until(
            lambda: _loot_at(client, session_id, 2, 2) is not None,
            timeout_s=10.0,
            interval_s=0.05,
        )
        res = client.post(
            f"/api/v1/boards/{session_id}/tokens/pc-ash/move",
            json={"to_x": 2, "to_y": 2},
        )
        assert res.status_code == 200, res.text
        assert (res.json()["x"], res.json()["y"]) == (2, 2)
        assert _tokens(client, session_id)["pc-ash"]["x"] == 2
