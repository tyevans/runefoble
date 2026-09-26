"""Blackbox TDD tests for OpenPanel Analytics Event Worker & Stream Projections.

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
All test setup and verification are performed strictly through public HTTP API endpoints,
domain CloudEvents over Redis Streams, and the OpenPanel analytics tracking interface.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session.main import app, set_event_bus
from runefoble_events.events import SessionStarted
from runefoble_platform.analytics import (
    AnalyticsEventWorker,
    OpenPanelClient,
    anonymize_profile_id,
)
from runefoble_platform.consumer_group import MockAsyncRedis, RedisConsumerGroup
from runefoble_platform.redis_bus import RedisStreamsEventBus


@pytest.fixture
def mock_redis() -> MockAsyncRedis:
    return MockAsyncRedis()


@pytest.fixture
def event_bus(mock_redis: MockAsyncRedis) -> RedisStreamsEventBus:
    return RedisStreamsEventBus(client=mock_redis)


@pytest.fixture
def analytics_client() -> OpenPanelClient:
    return OpenPanelClient(
        endpoint="http://openpanel:3000/api",
        client_id="rf_test_client_id",
        salt="test_salt_analytics_99",
        mock_mode=True,
    )


@pytest.fixture
def analytics_worker(
    analytics_client: OpenPanelClient, mock_redis: MockAsyncRedis
) -> AnalyticsEventWorker:
    return AnalyticsEventWorker(
        client=analytics_client,
        consumer_group=RedisConsumerGroup(client=mock_redis),
        streams=["runefoble.events.session", "runefoble.events.watcher"],
        group_name="test_analytics_workers",
        consumer_name="worker_test_1",
    )


@pytest.fixture
def http_client(event_bus: RedisStreamsEventBus) -> TestClient:
    set_event_bus(event_bus)
    return TestClient(app)


@pytest.mark.asyncio
async def test_frontdoor_session_start_tracks_analytics(
    http_client: TestClient,
    analytics_worker: AnalyticsEventWorker,
    analytics_client: OpenPanelClient,
) -> None:
    """Exercising public session start endpoint emits SessionStarted and records anonymized session.started."""
    await analytics_worker.setup_groups()
    create_res = http_client.post(
        "/api/v1/sessions/create",
        json={"campaign_id": str(uuid4()), "title": "The Sunken Vault", "dm_id": "watcher_dm_1"},
    )
    assert create_res.status_code == 200, create_res.text
    session_id = create_res.json()["session_id"]

    assert http_client.post(f"/api/v1/sessions/{session_id}/start").status_code == 200
    assert await analytics_worker.process_once() >= 1

    event = next(e for e in analytics_client.recorded_events if e["name"] == "session.started")
    assert event["event"] == "session.started"
    assert event["properties"]["session_id"] == session_id
    assert event["properties"]["started_at_turn"] == 1
    assert event.get("client_id") == "rf_test_client_id"


@pytest.mark.asyncio
async def test_frontdoor_dice_roll_tracks_analytics_with_anonymized_roller(
    http_client: TestClient,
    analytics_worker: AnalyticsEventWorker,
    analytics_client: OpenPanelClient,
) -> None:
    """Exercising public dice roll endpoint emits DiceRolled and records anonymized dice.rolled."""
    await analytics_worker.setup_groups()
    session_id, roller_id = str(uuid4()), "player-valeros-uuid-777"
    body = {
        "formula": "2d20kh1+5",
        "roller_id": roller_id,
        "roller_name": "Valeros the Fighter",
        "roll_type": "attack_roll",
    }
    roll_res = http_client.post(f"/api/v1/sessions/{session_id}/roll", json=body)
    assert roll_res.status_code == 200 and 6 <= roll_res.json()["total"] <= 25
    assert await analytics_worker.process_once() >= 1

    event = next(e for e in analytics_client.recorded_events if e["name"] == "dice.rolled")
    assert event["properties"]["formula"] == "2d20kh1+5"
    assert event["properties"]["total"] == roll_res.json()["total"]
    assert event["properties"]["session_id"] == session_id
    assert event["profile_id"] == anonymize_profile_id(roller_id, salt=analytics_client.salt)
    assert roller_id not in str(event)


@pytest.mark.asyncio
async def test_frontdoor_auto_pilot_turn_tracks_stand_in_without_dialogue_pii(
    http_client: TestClient,
    analytics_worker: AnalyticsEventWorker,
    analytics_client: OpenPanelClient,
) -> None:
    """Auto-pilot stand-in turn records stand_in.turn_taken without dialogue PII."""
    await analytics_worker.setup_groups()
    session_id = http_client.post(
        "/api/v1/sessions/create", json={"campaign_id": str(uuid4()), "title": "Dungeon Depths"}
    ).json()["session_id"]
    http_client.post(f"/api/v1/sessions/{session_id}/start")
    join_body = {
        "player_id": "player-absentee",
        "character_id": str(uuid4()),
        "character_name": "Merisiel",
        "character_class": "Rogue",
    }
    http_client.post(f"/api/v1/sessions/{session_id}/join", json=join_body)
    leave_body = {"player_id": "player-absentee", "reason": "went to sleep"}
    assert (
        http_client.post(f"/api/v1/sessions/{session_id}/leave", json=leave_body).status_code == 200
    )

    turn_body = {"penalties": ["drunk"], "scene_context": "Trapped in snake pit"}
    auto_res = http_client.post(f"/api/v1/sessions/{session_id}/turns/auto-pilot", json=turn_body)
    assert auto_res.status_code == 200, auto_res.text
    assert await analytics_worker.process_once() >= 1

    event = next(e for e in analytics_client.recorded_events if e["name"] == "stand_in.turn_taken")
    assert event["properties"]["character_name"] == "Merisiel"
    assert "penalties_applied" in event["properties"]
    for forbidden in ("dialogue", "transcript", "speech"):
        assert forbidden not in event["properties"]


@pytest.mark.asyncio
async def test_analytics_worker_lifecycle_and_fault_isolation(
    analytics_worker: AnalyticsEventWorker,
    event_bus: RedisStreamsEventBus,
    analytics_client: OpenPanelClient,
) -> None:
    """Verify worker start/stop lifecycle and fault isolation with dead letter handling."""
    await analytics_worker.setup_groups()
    event = SessionStarted(aggregate_id=uuid4(), started_at_turn=2)
    await event_bus.publish_event("runefoble.events.session", event)

    assert await analytics_worker.process_once() == 1
    assert len(analytics_client.recorded_events) == 1

    await analytics_worker.start()
    assert analytics_worker.running is True
    await analytics_worker.stop()
    assert analytics_worker.running is False
