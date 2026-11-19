"""Blackbox frontdoor tests: an approved audience hazard modifier places a board hazard (TASK-0835).

Setup uses the public campaign and board routes. The modifier is published as the standard
`AudienceModifierApproved` event on `runefoble.events.audience`. The result is read through the
public board read. Redis is the only double (MockAsyncRedis). The board_state consumers start
through the real lifespan. Governed by ADR-0006, ADR-0007, and ADR-0015.
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


def _modifier(
    campaign_id: str,
    session_id: str,
    *,
    approved: bool = True,
    modifier_type: str = "hazard_spawn",
    parameters: dict[str, Any] | None = None,
) -> AudienceModifierApproved:
    return AudienceModifierApproved(
        proposal_id=uuid4(),
        poll_id=uuid4(),
        campaign_id=campaign_id,
        session_id=session_id,
        approved_by="user-test",
        approved=approved,
        modifier_type=modifier_type,
        parameters=parameters
        if parameters is not None
        else {"x": 2, "y": 3, "hazard_type": "fire"},
    )


def _publish(stream_redis: MockAsyncRedis, event: AudienceModifierApproved) -> None:
    async def _send() -> None:
        await RedisStreamsEventBus(client=stream_redis).publish_event(AUDIENCE_STREAM, event)

    asyncio.run(_send())


def _hazard_at(client: TestClient, session_id: str, x: int, y: int) -> str | None:
    board = client.get(f"/api/v1/boards/{session_id}").json()
    cell = board["terrain_cells"].get(f"{x},{y}")
    return cell["hazard"] if cell else None


def test_approved_hazard_modifier_places_a_hazard_on_the_board(shared_redis: MockAsyncRedis):
    campaign_id = create_dm_campaign("user-test")
    session_id = f"sess-{uuid4().hex[:8]}"

    with TestClient(board_app, headers=bearer("user-test")) as client:
        assert client.get("/healthz").json()["consumers"] == {"board_state": "running"}
        _create_board(client, campaign_id, session_id)
        _publish(shared_redis, _modifier(campaign_id, session_id))

        assert wait_until(
            lambda: _hazard_at(client, session_id, 2, 3) == "fire",
            timeout_s=10.0,
            interval_s=0.05,
        )
        assert shared_redis.streams.get(AUDIENCE_DLQ, []) == []


def test_vetoed_hazard_and_weather_modifiers_change_nothing(shared_redis: MockAsyncRedis):
    campaign_id = create_dm_campaign("user-test")
    session_id = f"sess-{uuid4().hex[:8]}"

    with TestClient(board_app, headers=bearer("user-test")) as client:
        _create_board(client, campaign_id, session_id)
        _publish(
            shared_redis,
            _modifier(
                campaign_id,
                session_id,
                approved=False,
                parameters={"x": 2, "y": 3, "hazard_type": "fire"},
            ),
        )
        _publish(
            shared_redis,
            _modifier(
                campaign_id,
                session_id,
                modifier_type="weather_change",
                parameters={"x": 4, "y": 4, "hazard_type": "lava", "weather": "rain"},
            ),
        )
        # A later approved modifier is a barrier: the consumer reads the stream in order.
        _publish(
            shared_redis,
            _modifier(campaign_id, session_id, parameters={"x": 5, "y": 5, "hazard_type": "lava"}),
        )

        assert wait_until(
            lambda: _hazard_at(client, session_id, 5, 5) == "lava",
            timeout_s=10.0,
            interval_s=0.05,
        )
        assert _hazard_at(client, session_id, 2, 3) is None
        assert _hazard_at(client, session_id, 4, 4) is None
        assert shared_redis.streams.get(AUDIENCE_DLQ, []) == []


@pytest.mark.parametrize(
    ("parameters", "expected_reason"),
    [
        ({"x": 20, "y": 3, "hazard_type": "fire"}, "out of grid bounds"),
        ({"x": 2, "y": 3, "hazard_type": "dragon_breath"}, "unknown hazard"),
        ({"y": 3, "hazard_type": "fire"}, "'x'"),
    ],
    ids=["off_grid", "unknown_hazard", "missing_cell"],
)
def test_invalid_hazard_modifier_is_dead_lettered_and_changes_nothing(
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
        board = client.get(f"/api/v1/boards/{session_id}").json()
        assert board["terrain_cells"] == {}


def test_hazard_modifier_for_another_campaign_is_dead_lettered(shared_redis: MockAsyncRedis):
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
        assert client.get(f"/api/v1/boards/{session_id}").json()["terrain_cells"] == {}
