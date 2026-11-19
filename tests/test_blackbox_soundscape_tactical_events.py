"""Blackbox tests: tactical board events drive soundscape foley cues (TASK-0438).

Redis is an external process. Each test replaces only the Redis transport with MockAsyncRedis,
at the redis.asyncio.from_url boundary. The soundscape service starts through its real FastAPI
lifespan. Board events enter on the board stream, and results are read through the public
tension route and the soundscape output stream.

Governed by:
- ADR-0006: Redis Streams domain event streaming
- ADR-0007: Domain-driven design architecture
- ADR-0014: BDD and blackbox frontdoor tests
- AGENTS.md Hard Invariant 7: setup through frontdoors, assertions on public projections
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from typing import Any
from uuid import uuid4

import pytest
import redis.asyncio
from fastapi.testclient import TestClient
from runefoble_events.events import PhysicsCollisionOccurred, TokenHazardTriggered
from runefoble_platform.redis_bus import RedisStreamsEventBus

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.polling import wait_until
from tests.helpers.ws_identity import bearer

BOARD_STREAM = "runefoble.events.board"
SOUNDSCAPE_OUTPUT_STREAM = "runefoble.events.soundscape"
CUE_TRIGGERED_TYPE = "runefoble.events.soundscape.cue_triggered"


@pytest.fixture
def redis_double(monkeypatch: pytest.MonkeyPatch) -> MockAsyncRedis:
    """Route every service-created Redis client to one in-memory transport double."""
    double = MockAsyncRedis()
    monkeypatch.setattr(redis.asyncio, "from_url", lambda *_args, **_kwargs: double)
    return double


def _publish(double: MockAsyncRedis, stream: str, event: Any) -> None:
    asyncio.run(RedisStreamsEventBus(client=double).publish_event(stream, event))


def _recent_cues(client: TestClient, session_id: str) -> list[dict[str, Any]]:
    url = f"/api/v1/soundscape/tension?session_id={session_id}"
    return client.get(url).json()["recent_cues"]


def test_hazard_trigger_on_board_stream_records_hazard_cue(
    redis_double: MockAsyncRedis, use_redis_client: Callable[[object], object]
) -> None:
    """A TokenHazardTriggered on the board stream records a hazard cue for its session."""
    from soundscape.main import app

    session_id = str(uuid4())
    use_redis_client(redis_double)

    with TestClient(app, headers=bearer("soundscape-tester")) as client:
        assert client.get("/healthz").json()["consumers"] == {"soundscape": "running"}
        _publish(
            redis_double,
            BOARD_STREAM,
            TokenHazardTriggered(
                session_id=session_id,
                board_id="board-hazard",
                token_id="tok-hero",
                hazard_type="lava",
                damage_dice="2d10",
            ),
        )

        def hazard_cue_recorded() -> bool:
            return any(
                cue["sound_url"].endswith("/hazard_lava.ogg")
                for cue in _recent_cues(client, session_id)
            )

        assert wait_until(hazard_cue_recorded, timeout_s=10.0), "no hazard cue was recorded"
        cues = _recent_cues(client, session_id)
        hazard = next(cue for cue in cues if cue["sound_url"].endswith("/hazard_lava.ogg"))
        assert hazard["cue_type"] == "sfx"
        assert hazard["volume_gain"] == 1.0


def test_physics_collision_records_impact_cue_scaled_by_energy(
    redis_double: MockAsyncRedis, use_redis_client: Callable[[object], object]
) -> None:
    """A hard collision records a louder impact cue than a soft one."""
    from soundscape.main import app

    session_id = str(uuid4())
    use_redis_client(redis_double)

    with TestClient(app, headers=bearer("soundscape-tester")) as client:
        for energy in (5.0, 200.0):
            _publish(
                redis_double,
                BOARD_STREAM,
                PhysicsCollisionOccurred(
                    session_id=session_id,
                    board_id="board-physics",
                    entity_id="tok-ogre",
                    collision_type="wall",
                    x=3.0,
                    y=4.0,
                    impact_velocity=10.0,
                    impact_energy=energy,
                ),
            )

        def two_impact_cues_recorded() -> bool:
            impacts = [
                cue
                for cue in _recent_cues(client, session_id)
                if cue["sound_url"].endswith("/impact_wall.ogg")
            ]
            return len(impacts) >= 2

        assert wait_until(two_impact_cues_recorded, timeout_s=10.0), "impact cues not recorded"
        gains = sorted(
            cue["volume_gain"]
            for cue in _recent_cues(client, session_id)
            if cue["sound_url"].endswith("/impact_wall.ogg")
        )
        assert gains[0] < gains[-1]
        assert gains[0] > 0.0


def test_recorded_tactical_cue_is_published_on_soundscape_stream(
    redis_double: MockAsyncRedis, use_redis_client: Callable[[object], object]
) -> None:
    """A tactical cue is published as SoundscapeCueTriggered with the session and sound URL."""
    from soundscape.main import app

    session_id = str(uuid4())
    use_redis_client(redis_double)

    with TestClient(app, headers=bearer("soundscape-tester")):
        _publish(
            redis_double,
            BOARD_STREAM,
            TokenHazardTriggered(
                session_id=session_id,
                board_id="board-publish",
                token_id="tok-rogue",
                hazard_type="spike_pit",
                damage_dice="1d6",
            ),
        )

        def cue_entries() -> list[dict[str, Any]]:
            fields = [entry[1] for entry in redis_double.streams.get(SOUNDSCAPE_OUTPUT_STREAM, [])]
            return [
                item
                for item in fields
                if item.get("event_type") == CUE_TRIGGERED_TYPE
                and json.loads(item["payload"]).get("session_id") == session_id
            ]

        assert wait_until(lambda: len(cue_entries()) >= 1, timeout_s=10.0), (
            "no cue event reached the stream"
        )
        entry = cue_entries()[0]
        payload = json.loads(entry["payload"])
        assert payload["sound_url"].endswith("/hazard_spike_pit.ogg")
        assert payload["cue_type"] == "sfx"
