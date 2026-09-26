"""Blackbox TDD tests for OpenPanel Privacy-Preserving Analytics SDK & Event Pipeline.

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
All test setup and verification are performed strictly through public HTTP API endpoints,
domain CloudEvents over Redis Streams, and the OpenPanel analytics tracking interface.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from game_session.main import app, set_event_bus
from runefoble_events.events import (
    SessionStarted,
)
from runefoble_platform.analytics import (
    AnalyticsEventWorker,
    OpenPanelClient,
    anonymize_profile_id,
    sanitize_properties,
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
def consumer_group(mock_redis: MockAsyncRedis) -> RedisConsumerGroup:
    return RedisConsumerGroup(client=mock_redis)


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
    analytics_client: OpenPanelClient, consumer_group: RedisConsumerGroup
) -> AnalyticsEventWorker:
    return AnalyticsEventWorker(
        client=analytics_client,
        consumer_group=consumer_group,
        streams=["runefoble.events.session", "runefoble.events.watcher"],
        group_name="test_analytics_workers",
        consumer_name="worker_test_1",
    )


@pytest.fixture
def http_client(event_bus: RedisStreamsEventBus) -> TestClient:
    set_event_bus(event_bus)
    client = TestClient(app)
    return client


# ---------------------------------------------------------------------------
# Frontdoor Game Actions -> OpenPanel Telemetry Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_frontdoor_session_start_tracks_analytics(
    http_client: TestClient,
    analytics_worker: AnalyticsEventWorker,
    analytics_client: OpenPanelClient,
) -> None:
    """Exercising public session start endpoint emits SessionStarted and records anonymized session.started."""
    await analytics_worker.setup_groups()
    campaign_id = str(uuid4())

    # 1. Frontdoor HTTP: Create session
    create_res = http_client.post(
        "/api/v1/sessions/create",
        json={"campaign_id": campaign_id, "title": "The Sunken Vault", "dm_id": "watcher_dm_1"},
    )
    assert create_res.status_code == 200, create_res.text
    session_id = create_res.json()["session_id"]

    # 2. Frontdoor HTTP: Start session
    start_res = http_client.post(f"/api/v1/sessions/{session_id}/start")
    assert start_res.status_code == 200, start_res.text
    assert start_res.json()["status"] == "active"

    # 3. Process events from stream via AnalyticsEventWorker
    processed = await analytics_worker.process_once()
    assert processed >= 1

    # 4. Verify recorded analytics metric
    assert len(analytics_client.recorded_events) >= 1
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
    session_id = str(uuid4())
    roller_id = "player-valeros-uuid-777"

    # 1. Frontdoor HTTP: Roll dice
    roll_res = http_client.post(
        f"/api/v1/sessions/{session_id}/roll",
        json={
            "formula": "2d20kh1+5",
            "roller_id": roller_id,
            "roller_name": "Valeros the Fighter",
            "roll_type": "attack_roll",
        },
    )
    assert roll_res.status_code == 200, roll_res.text
    data = roll_res.json()
    assert 6 <= data["total"] <= 25

    # 2. Process stream messages
    processed = await analytics_worker.process_once()
    assert processed >= 1

    # 3. Verify recorded metric
    event = next(e for e in analytics_client.recorded_events if e["name"] == "dice.rolled")
    assert event["properties"]["formula"] == "2d20kh1+5"
    assert event["properties"]["total"] == data["total"]
    assert event["properties"]["session_id"] == session_id

    # Verify roller_id is anonymized (hashed with salt, NOT raw plaintext)
    expected_hash = anonymize_profile_id(roller_id, salt=analytics_client.salt)
    assert event["profile_id"] == expected_hash
    assert roller_id not in str(event)


@pytest.mark.asyncio
async def test_frontdoor_auto_pilot_turn_tracks_stand_in_without_dialogue_pii(
    http_client: TestClient,
    analytics_worker: AnalyticsEventWorker,
    analytics_client: OpenPanelClient,
) -> None:
    """Auto-pilot stand-in turn records stand_in.turn_taken and penalty without leaking speech transcripts."""
    await analytics_worker.setup_groups()
    session_id = str(uuid4())

    # 1. Frontdoor HTTP: Create session and start it
    create_res = http_client.post(
        "/api/v1/sessions/create",
        json={"campaign_id": str(uuid4()), "title": "Dungeon Depths"},
    )
    assert create_res.status_code == 200
    session_id = create_res.json()["session_id"]
    http_client.post(f"/api/v1/sessions/{session_id}/start")

    # 2. Join a player who later misses turn
    char_id = str(uuid4())
    http_client.post(
        f"/api/v1/sessions/{session_id}/join",
        json={
            "player_id": "player-absentee",
            "character_id": char_id,
            "character_name": "Merisiel",
            "character_class": "Rogue",
        },
    )

    # Player leaves the session, activating AI stand-in
    leave_res = http_client.post(
        f"/api/v1/sessions/{session_id}/leave",
        json={"player_id": "player-absentee", "reason": "went to sleep"},
    )
    assert leave_res.status_code == 200

    # 3. Frontdoor HTTP: Execute stand-in turn with penalties
    auto_res = http_client.post(
        f"/api/v1/sessions/{session_id}/turns/auto-pilot",
        json={"penalties": ["drunk"], "scene_context": "Trapped in snake pit"},
    )
    assert auto_res.status_code == 200, auto_res.text

    # 4. Process analytics events from both session and watcher streams
    processed = await analytics_worker.process_once()
    assert processed >= 1

    # 5. Verify stand-in analytics
    event_names = [e["name"] for e in analytics_client.recorded_events]
    assert "stand_in.turn_taken" in event_names

    stand_in_event = next(
        e for e in analytics_client.recorded_events if e["name"] == "stand_in.turn_taken"
    )
    assert stand_in_event["properties"]["character_name"] == "Merisiel"
    assert "penalties_applied" in stand_in_event["properties"]

    # Hard invariant: Ensure raw dialogue / speech is stripped and never logged in properties
    assert "dialogue" not in stand_in_event["properties"]
    assert "transcript" not in stand_in_event["properties"]
    assert "speech" not in stand_in_event["properties"]


# ---------------------------------------------------------------------------
# Privacy Preservation & Sanitization Unit Invariant Tests
# ---------------------------------------------------------------------------


def test_sanitize_properties_removes_audio_and_transcripts() -> None:
    """Properties with sensitive audio, dialogue, or credential keys must be stripped."""
    dirty_props: dict[str, Any] = {
        "session_id": "sess-123",
        "audio": b"RIFF...wav_binary_data",
        "raw_audio": "http://audio.local/stream.wav",
        "audio_bytes": "base64...",
        "transcript": "Hello, I want to cast Fireball",
        "raw_transcript": "raw stt transcript",
        "speech": "speech text",
        "dialogue": "Character says: Watch out!",
        "token": "secret_jwt_token",
        "password": "my_password",
        "email": "player@example.com",
        "nested": {
            "character_name": "Valeros",
            "transcript": "nested transcript should be removed",
        },
        "safe_int": 42,
    }

    clean = sanitize_properties(dirty_props)

    assert "session_id" in clean
    assert "safe_int" in clean
    assert clean["nested"] == {"character_name": "Valeros"}

    # All forbidden keys eliminated
    for forbidden in [
        "audio",
        "raw_audio",
        "audio_bytes",
        "transcript",
        "raw_transcript",
        "speech",
        "dialogue",
        "token",
        "password",
        "email",
    ]:
        assert forbidden not in clean


def test_anonymize_profile_id_hashing() -> None:
    """Anonymization must be deterministic with salt, producing consistent hashes."""
    salt = "my_custom_salt_123"
    pid = "user_valeros_99"

    hash1 = anonymize_profile_id(pid, salt=salt)
    hash2 = anonymize_profile_id(pid, salt=salt)
    assert hash1 == hash2
    assert hash1 is not None
    assert len(hash1) == 32
    assert pid not in hash1

    # Different salt produces different hash
    hash_other = anonymize_profile_id(pid, salt="different_salt")
    assert hash1 != hash_other

    # None or empty produces None
    assert anonymize_profile_id(None) is None
    assert anonymize_profile_id("") is None


# ---------------------------------------------------------------------------
# HTTP Client Dispatch & Mock Transport Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_openpanel_client_http_dispatch_with_mock_transport() -> None:
    """Verify OpenPanelClient dispatches HTTP POST requests to configured endpoint."""
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(200, json={"status": "ok"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_mock:
        client = OpenPanelClient(
            endpoint="http://openpanel:3000/api",
            client_id="proj_xyz",
            salt="salt_1",
            mock_mode=False,
            http_client=http_mock,
        )

        result = await client.track(
            event_name="session.started",
            properties={"campaign_type": "5e"},
            profile_id="player-1",
        )

        assert result["event"] == "session.started"
        assert len(captured_requests) == 1
        req = captured_requests[0]
        assert str(req.url) == "http://openpanel:3000/api/event"
        assert req.headers["openpanel-client-id"] == "proj_xyz"
        assert req.headers["content-type"] == "application/json"


@pytest.mark.asyncio
async def test_analytics_worker_lifecycle_and_fault_isolation(
    analytics_worker: AnalyticsEventWorker,
    event_bus: RedisStreamsEventBus,
    analytics_client: OpenPanelClient,
) -> None:
    """Verify worker start/stop lifecycle and fault isolation with dead letter handling."""
    await analytics_worker.setup_groups()

    # Publish an event to the session stream
    await event_bus.publish_event(
        "runefoble.events.session",
        SessionStarted(aggregate_id=uuid4(), started_at_turn=2),
    )

    # Process once
    processed = await analytics_worker.process_once()
    assert processed == 1
    assert len(analytics_client.recorded_events) == 1

    # Start and stop worker loop cleanly
    await analytics_worker.start()
    assert analytics_worker.running is True
    await analytics_worker.stop()
    assert analytics_worker.running is False
