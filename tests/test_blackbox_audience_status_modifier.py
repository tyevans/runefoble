"""Blackbox frontdoor tests: an approved audience status modifier applies a condition (TASK-0836).

Setup uses the public character routes. The modifier is published as the standard
`AudienceModifierApproved` event on `runefoble.events.audience`. The result is read through the
public character read. Redis is the only double (MockAsyncRedis). The consumer starts through the
real character_sheet lifespan. Governed by ADR-0006, ADR-0007, and ADR-0015.
"""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from typing import Any
from uuid import uuid4

import pytest
import redis.asyncio
from character_sheet.main import app as character_app
from fastapi.testclient import TestClient
from runefoble_events.events import AudienceModifierApproved
from runefoble_platform.redis_bus import RedisStreamsEventBus

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.polling import wait_until
from tests.helpers.ws_identity import SIGNING_ISSUER

AUDIENCE_STREAM = "runefoble.events.audience"
AUDIENCE_DLQ = f"{AUDIENCE_STREAM}.dlq"


@pytest.fixture
def stream_redis(mock_bus, monkeypatch: pytest.MonkeyPatch) -> MockAsyncRedis:
    """One Redis double for the publisher and the character_sheet lifespan consumer."""
    monkeypatch.setattr(redis.asyncio, "from_url", lambda *_args, **_kwargs: mock_bus)
    return mock_bus


@pytest.fixture
def client(stream_redis: MockAsyncRedis) -> Generator[TestClient]:
    """Run the real lifespan, so the audience consumer starts and reads the stream."""
    headers = {"Authorization": f"Bearer {SIGNING_ISSUER.mint('character-owner')}"}
    with TestClient(character_app, headers=headers) as test_client:
        assert test_client.get("/healthz").json()["consumers"] == {"character_sheet": "running"}
        yield test_client


def _create_character(client: TestClient, campaign_id: str) -> str:
    res = client.post(
        "/api/v1/characters",
        json={
            "name": "Valeros",
            "character_class": "Fighter",
            "max_hp": 30,
            "campaign_id": campaign_id,
        },
    )
    assert res.status_code == 200, res.text
    return res.json()["character_id"]


def _approved(
    campaign_id: str,
    *,
    approved: bool = True,
    modifier_type: str = "status_buff",
    parameters: dict[str, Any] | None = None,
) -> AudienceModifierApproved:
    return AudienceModifierApproved(
        proposal_id=uuid4(),
        poll_id=uuid4(),
        campaign_id=campaign_id,
        session_id=None,
        approved_by="dm-evelyn",
        approved=approved,
        modifier_type=modifier_type,
        parameters=parameters if parameters is not None else {},
    )


def _publish(stream_redis: MockAsyncRedis, event: AudienceModifierApproved) -> None:
    async def _send() -> None:
        await RedisStreamsEventBus(client=stream_redis).publish_event(AUDIENCE_STREAM, event)

    asyncio.run(_send())


def _conditions(client: TestClient, character_id: str) -> dict[str, Any]:
    return client.get(f"/api/v1/characters/{character_id}").json()["conditions"]


def test_approved_status_buff_applies_the_condition_to_the_character(client, stream_redis) -> None:
    campaign_id = str(uuid4())
    character_id = _create_character(client, campaign_id)
    _publish(
        stream_redis,
        _approved(
            campaign_id,
            parameters={"character_id": character_id, "condition": "blessed"},
        ),
    )

    assert wait_until(
        lambda: "blessed" in _conditions(client, character_id),
        timeout_s=10.0,
        interval_s=0.05,
    )
    assert stream_redis.streams.get(AUDIENCE_DLQ, []) == []


def test_vetoed_status_buff_changes_nothing(client, stream_redis) -> None:
    campaign_id = str(uuid4())
    character_id = _create_character(client, campaign_id)
    _publish(
        stream_redis,
        _approved(
            campaign_id,
            approved=False,
            parameters={"character_id": character_id, "condition": "blessed"},
        ),
    )
    # A later approved modifier is a barrier: the consumer reads the stream in order.
    _publish(
        stream_redis,
        _approved(
            campaign_id,
            parameters={"character_id": character_id, "condition": "inspired"},
        ),
    )

    assert wait_until(
        lambda: "inspired" in _conditions(client, character_id),
        timeout_s=10.0,
        interval_s=0.05,
    )
    assert "blessed" not in _conditions(client, character_id)
    assert stream_redis.streams.get(AUDIENCE_DLQ, []) == []


def test_other_modifier_types_are_left_to_their_owners(client, stream_redis) -> None:
    campaign_id = str(uuid4())
    character_id = _create_character(client, campaign_id)
    _publish(
        stream_redis,
        _approved(
            campaign_id,
            modifier_type="weather_change",
            parameters={"character_id": character_id, "condition": "blessed", "weather": "rain"},
        ),
    )
    _publish(
        stream_redis,
        _approved(
            campaign_id,
            parameters={"character_id": character_id, "condition": "inspired"},
        ),
    )

    assert wait_until(
        lambda: "inspired" in _conditions(client, character_id),
        timeout_s=10.0,
        interval_s=0.05,
    )
    assert "blessed" not in _conditions(client, character_id)
    assert stream_redis.streams.get(AUDIENCE_DLQ, []) == []


def test_status_buff_for_a_character_of_another_campaign_is_dead_lettered(
    client, stream_redis
) -> None:
    campaign_id = str(uuid4())
    character_id = _create_character(client, campaign_id)
    _publish(
        stream_redis,
        _approved(
            str(uuid4()),
            parameters={"character_id": character_id, "condition": "blessed"},
        ),
    )

    assert wait_until(
        lambda: bool(stream_redis.streams.get(AUDIENCE_DLQ)),
        timeout_s=10.0,
        interval_s=0.05,
    )
    (_entry_id, dead_letter), *_ = stream_redis.streams[AUDIENCE_DLQ]
    assert "campaign" in dead_letter["error_reason"]
    assert _conditions(client, character_id) == {}


@pytest.mark.parametrize(
    ("build_parameters", "reason_fragment"),
    [
        pytest.param(lambda _cid: {"condition": "blessed"}, "character_id", id="missing-character"),
        pytest.param(
            lambda _cid: {"character_id": "not-a-uuid", "condition": "blessed"},
            "UUID",
            id="bad-id",
        ),
        pytest.param(lambda cid: {"character_id": cid}, "condition", id="missing-condition"),
        pytest.param(
            lambda cid: {"character_id": cid, "condition": "dragonfire"},
            "dragonfire",
            id="unknown-condition",
        ),
    ],
)
def test_invalid_status_buff_is_dead_lettered(
    client, stream_redis, build_parameters, reason_fragment: str
) -> None:
    campaign_id = str(uuid4())
    character_id = _create_character(client, campaign_id)
    _publish(stream_redis, _approved(campaign_id, parameters=build_parameters(character_id)))

    assert wait_until(
        lambda: bool(stream_redis.streams.get(AUDIENCE_DLQ)),
        timeout_s=10.0,
        interval_s=0.05,
    )
    (_entry_id, dead_letter), *_ = stream_redis.streams[AUDIENCE_DLQ]
    assert reason_fragment in dead_letter["error_reason"]
    assert _conditions(client, character_id) == {}
