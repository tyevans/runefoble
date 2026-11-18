"""Real-Redis blackbox test for the character health stream (TASK-0574).

A health change made through the character sheet public route lands in a real Redis Stream
with its session and campaign ids. The test uses a Redis container, so it needs Docker and
is marked `docker`. Run it with: uv run pytest -m docker tests/test_blackbox_character_health_real_redis.py

Governed by ADR-0006 (Redis Streams transport) and Hard Invariant 7.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from uuid import uuid4

import pytest
import redis
from character_sheet.main import app
from fastapi.testclient import TestClient
from runefoble_platform.redis_bus import RedisStreamsEventBus

from tests.helpers.postgres import get_free_port
from tests.helpers.redis_container import redis_container
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = [pytest.mark.docker, pytest.mark.usefixtures("trusted_ws_issuer")]

CHARACTER_STREAM = "runefoble.events.character"


@pytest.fixture
def real_redis_url() -> Iterator[str]:
    with redis_container(get_free_port()) as url:
        yield url


def test_health_change_reaches_a_real_redis_stream_with_session_and_campaign(
    real_redis_url: str,
    use_event_bus,
) -> None:
    bus = RedisStreamsEventBus(redis_url=real_redis_url)
    use_event_bus(bus)
    session_id, campaign_id = str(uuid4()), str(uuid4())
    headers = {"Authorization": f"Bearer {SIGNING_ISSUER.mint('character-owner')}"}
    # One TestClient context keeps one event loop for the Redis connection it creates.
    with TestClient(app, headers=headers) as client:
        created = client.post(
            "/api/v1/characters",
            json={
                "name": "Valeros",
                "character_class": "Fighter",
                "max_hp": 30,
                "campaign_id": campaign_id,
            },
        )
        assert created.status_code == 200, created.text
        char_id = created.json()["character_id"]

        hit = client.post(
            f"/api/v1/characters/{char_id}/health",
            json={"delta": -7, "source": "Goblin Arrow", "session_id": session_id},
        )
        assert hit.status_code == 200, hit.text

    raw = redis.Redis.from_url(real_redis_url, decode_responses=True)
    health = [
        json.loads(fields["payload"])
        for _id, fields in raw.xrange(CHARACTER_STREAM)
        if fields.get("event_type") == "CharacterHealthChanged"
        and json.loads(fields["payload"]).get("aggregate_id") == char_id
    ]
    assert len(health) == 1
    assert health[0]["session_id"] == session_id
    assert health[0]["campaign_id"] == campaign_id
    assert health[0]["delta"] == -7
