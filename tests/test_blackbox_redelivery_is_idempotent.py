"""Blackbox frontdoor tests: a redelivered stream message changes nothing the second time (TASK-0854).

A reclaimed message runs its handler again. Each test publishes the same domain event twice on
the public stream, then a later event as a barrier. The stream is read in order, so the barrier
proves that both deliveries were processed. The result is read through public routes or stream
reads. Redis is the only double (MockAsyncRedis). Governed by ADR-0006, ADR-0011, and Hard
Invariant 7.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Generator
from typing import Any
from uuid import uuid4

import pytest
import redis.asyncio
from board_state.main import app as board_app
from character_sheet.main import app as character_app
from fastapi.testclient import TestClient
from runefoble_events.asset import BattlemapForged
from runefoble_events.events import AudienceModifierApproved, DiceRolled
from runefoble_platform.redis_bus import RedisStreamsEventBus
from soundscape.event_handlers import handle_incoming_domain_event
from soundscape.session_state import read_session_state

from tests.helpers.campaign_setup import create_dm_campaign
from tests.helpers.game_session_app import session_app
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.polling import wait_until
from tests.helpers.ws_identity import SIGNING_ISSUER, bearer

AUDIENCE_STREAM = "runefoble.events.audience"
AUDIENCE_DLQ = f"{AUDIENCE_STREAM}.dlq"
SESSION_STREAM = "runefoble.events.session"
BOARD_STREAM = "runefoble.events.board"
ASSET_STREAM = "runefoble.events.asset"
WEATHER_EVENT = "runefoble.events.session.weather_changed"
TERRAIN_EVENT = "runefoble.events.board.terrain_modified"
FORGED_EVENT = "runefoble.events.board.forged_battlemap_applied"

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.fixture
def shared_redis(mock_bus: MockAsyncRedis, monkeypatch: pytest.MonkeyPatch) -> MockAsyncRedis:
    """One Redis double for the publisher and every service lifespan consumer in the test."""
    monkeypatch.setattr(redis.asyncio, "from_url", lambda *_args, **_kwargs: mock_bus)
    return mock_bus


def _publish(stream_redis: MockAsyncRedis, stream: str, event: Any) -> None:
    async def _send() -> None:
        await RedisStreamsEventBus(client=stream_redis).publish_event(stream, event)

    asyncio.run(_send())


def _payloads(stream_redis: MockAsyncRedis, stream: str, event_type: str) -> list[dict[str, Any]]:
    """Return the decoded payloads of one event type on one stream, in stream order."""
    matches: list[dict[str, Any]] = []
    for _entry_id, fields in stream_redis.streams.get(stream, []):
        if fields["event_type"] == event_type:
            matches.append(json.loads(fields["payload"]))
    return matches


# Game session: an approved weather modifier.


@pytest.fixture
def session_client(shared_redis: MockAsyncRedis) -> Generator[TestClient]:
    headers = {"Authorization": f"Bearer {SIGNING_ISSUER.mint('dm-evelyn')}"}
    with TestClient(session_app, headers=headers) as client:
        assert client.get("/healthz").json()["consumers"] == {"game_session": "running"}
        yield client


def _weather_modifier(campaign_id: str, session_id: str, weather: str) -> AudienceModifierApproved:
    return AudienceModifierApproved(
        proposal_id=uuid4(),
        poll_id=uuid4(),
        campaign_id=campaign_id,
        session_id=session_id,
        approved_by="dm-evelyn",
        approved=True,
        modifier_type="weather_change",
        parameters={"weather": weather},
    )


def test_redelivered_weather_modifier_records_one_weather_change(
    session_client: TestClient, shared_redis: MockAsyncRedis
) -> None:
    campaign = session_client.post("/api/v1/campaigns", json={"title": "Tomb"})
    assert campaign.status_code == 201, campaign.text
    campaign_id = campaign.json()["id"]
    session = session_client.post(
        f"/api/v1/campaigns/{campaign_id}/sessions", json={"title": "Crypt"}
    )
    assert session.status_code == 201, session.text
    session_id = session.json()["id"]

    fog = _weather_modifier(campaign_id, session_id, "dense fog")
    _publish(shared_redis, AUDIENCE_STREAM, fog)
    _publish(shared_redis, AUDIENCE_STREAM, fog)  # the redelivery
    _publish(shared_redis, AUDIENCE_STREAM, _weather_modifier(campaign_id, session_id, "rain"))

    def rain_applied() -> bool:
        return session_client.get(f"/api/v1/sessions/{session_id}").json()["weather"] == "rain"

    assert wait_until(rain_applied, timeout_s=10.0, interval_s=0.05)
    changes = [
        event["weather"]
        for event in _payloads(shared_redis, SESSION_STREAM, WEATHER_EVENT)
        if str(event.get("session_id")) == session_id
    ]
    assert changes == ["dense fog", "rain"]
    assert shared_redis.streams.get(AUDIENCE_DLQ, []) == []


# Board state: an approved hazard modifier.


def test_redelivered_hazard_modifier_records_one_terrain_change(
    shared_redis: MockAsyncRedis,
) -> None:
    campaign_id = create_dm_campaign("user-test")
    session_id = f"sess-{uuid4().hex[:8]}"
    hazard = AudienceModifierApproved(
        proposal_id=uuid4(),
        poll_id=uuid4(),
        campaign_id=campaign_id,
        session_id=session_id,
        approved_by="user-test",
        approved=True,
        modifier_type="hazard_spawn",
        parameters={"x": 2, "y": 3, "hazard_type": "fire"},
    )

    with TestClient(board_app, headers=bearer("user-test")) as client:
        res = client.post(
            "/api/v1/boards",
            json={"campaign_id": campaign_id, "session_id": session_id, "cols": 16, "rows": 16},
        )
        assert res.status_code == 200, res.text

        _publish(shared_redis, AUDIENCE_STREAM, hazard)
        _publish(shared_redis, AUDIENCE_STREAM, hazard)  # the redelivery
        barrier = hazard.model_copy(
            update={
                "proposal_id": uuid4(),
                "parameters": {"x": 5, "y": 5, "hazard_type": "fire"},
            }
        )
        _publish(shared_redis, AUDIENCE_STREAM, barrier)

        def barrier_applied() -> bool:
            board = client.get(f"/api/v1/boards/{session_id}").json()
            return board["terrain_cells"].get("5,5", {}).get("hazard") == "fire"

        assert wait_until(barrier_applied, timeout_s=10.0, interval_s=0.05)

    cell_changes = [
        event
        for event in _payloads(shared_redis, BOARD_STREAM, TERRAIN_EVENT)
        if (event["x"], event["y"]) == (2, 3)
    ]
    assert len(cell_changes) == 1
    assert shared_redis.streams.get(AUDIENCE_DLQ, []) == []


# Board state: a forged battlemap.


def test_redelivered_forged_battlemap_applies_once(shared_redis: MockAsyncRedis) -> None:
    campaign_id = create_dm_campaign("user-test")
    session_id = f"sess-{uuid4().hex[:8]}"
    forged = BattlemapForged(
        asset_id=f"map-{uuid4().hex[:8]}",
        campaign_id=campaign_id,
        session_id=session_id,
        creator_id="user-test",
        prompt="Flooded crypt",
        image_url="http://silo:9000/runefoble-assets/battlemaps/flooded.png",
        width_cells=12,
        height_cells=12,
        cell_size_px=64,
    )

    with TestClient(board_app, headers=bearer("user-test")) as client:
        res = client.post(
            "/api/v1/boards",
            json={"campaign_id": campaign_id, "session_id": session_id, "cols": 8, "rows": 8},
        )
        assert res.status_code == 200, res.text

        _publish(shared_redis, ASSET_STREAM, forged)
        _publish(shared_redis, ASSET_STREAM, forged)  # the redelivery
        barrier = forged.model_copy(update={"asset_id": f"map-{uuid4().hex[:8]}"})
        _publish(shared_redis, ASSET_STREAM, barrier)

        def barrier_applied() -> bool:
            return len(_payloads(shared_redis, BOARD_STREAM, FORGED_EVENT)) >= 2

        assert wait_until(barrier_applied, timeout_s=10.0, interval_s=0.05)

    applied = [event["asset_id"] for event in _payloads(shared_redis, BOARD_STREAM, FORGED_EVENT)]
    assert applied == [forged.asset_id, barrier.asset_id]
    assert shared_redis.streams.get(f"{ASSET_STREAM}.dlq", []) == []


# Character sheet: an approved status buff.


def test_redelivered_status_buff_keeps_the_one_condition(
    shared_redis: MockAsyncRedis, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without a public event for conditions, the test checks the state a redelivery leaves."""
    headers = {"Authorization": f"Bearer {SIGNING_ISSUER.mint('character-owner')}"}
    campaign_id = str(uuid4())
    buff = AudienceModifierApproved(
        proposal_id=uuid4(),
        poll_id=uuid4(),
        campaign_id=campaign_id,
        session_id=None,
        approved_by="dm-evelyn",
        approved=True,
        modifier_type="status_buff",
        parameters={"character_id": "", "condition": "blessed"},
    )

    with TestClient(character_app, headers=headers) as client:
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
        character_id = created.json()["character_id"]
        buff = buff.model_copy(
            update={"parameters": {"character_id": character_id, "condition": "blessed"}}
        )

        _publish(shared_redis, AUDIENCE_STREAM, buff)
        _publish(shared_redis, AUDIENCE_STREAM, buff)  # the redelivery
        barrier = buff.model_copy(
            update={
                "proposal_id": uuid4(),
                "parameters": {"character_id": character_id, "condition": "inspired"},
            }
        )
        _publish(shared_redis, AUDIENCE_STREAM, barrier)

        def inspired_applied() -> bool:
            conditions = client.get(f"/api/v1/characters/{character_id}").json()["conditions"]
            return "inspired" in conditions

        assert wait_until(inspired_applied, timeout_s=10.0, interval_s=0.05)
        conditions = client.get(f"/api/v1/characters/{character_id}").json()["conditions"]
        assert conditions["blessed"]["source"] == f"audience:{buff.proposal_id}"
    assert shared_redis.streams.get(AUDIENCE_DLQ, []) == []


# Soundscape: a source event feeds the session once.


@pytest.mark.asyncio
async def test_redelivered_critical_hit_triggers_one_leitmotif() -> None:
    session_id = f"session-redeliver-{uuid4().hex[:8]}"
    crit = DiceRolled(
        session_id=session_id,
        roller_id="char-valeros",
        roller_name="Valeros",
        formula="1d20",
        total=20,
        rolls=[20],
        is_crit=True,
    )

    await handle_incoming_domain_event(crit)
    await handle_incoming_domain_event(crit)  # the redelivery

    state = await read_session_state(session_id)
    assert [entry["motif_type"] for entry in state.leitmotif_history] == ["triumphant"]
    assert state.handled_source_event_ids == [str(crit.event_id)]
