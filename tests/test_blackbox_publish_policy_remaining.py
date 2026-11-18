"""Blackbox tests for the publish failure policy at the remaining sites (TASK-0693).

Domain-state sites fail the request with 503 and record nothing. Notification sites succeed
and count each failed delivery on ``/healthz``. A failed transcription engine publishes
``VoiceTranscriptionFailed`` through the public transcribe route.

The failing Redis client is a process-boundary double. Every other path uses public HTTP,
WebSocket or stream frontdoors.
"""

from __future__ import annotations

import asyncio
import base64
import uuid
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from gateway_mcp.dynamic import get_event_bus as get_dynamic_event_bus
from gateway_mcp.dynamic import set_event_bus as set_dynamic_event_bus
from gateway_mcp.dynamic.events import publish_system_event
from gateway_mcp.server import configure_dynamic_event_bus, mcp
from runefoble_events.events import PlayerSpokeEvent, VoiceTranscriptionFailed
from runefoble_events.mcp_tools import DynamicToolUnregisteredEvent
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_bus import EventBusUnavailableError
from runefoble_platform.redis_bus import RedisStreamsEventBus, deserialize_event
from voice_agent.main import app as voice_app
from voice_agent.main import set_event_bus as voice_set_event_bus
from voice_agent.stt import set_streaming_pipeline

from tests.helpers.audio_synth import generate_pcm_sine
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.voice_identity import voice_auth_headers, voice_ws_subprotocols

pytestmark = pytest.mark.usefixtures("trusted_voice_issuer")

TRANSCRIBE_URL = "/api/v1/voice/transcribe"
BARGE_IN_URL = "/api/v1/voice/filters/barge-in/evaluate"
SESSION_STREAM = "runefoble.events.session"
VOICE_STREAM = "runefoble.events.voice"


class FailingRedis(MockAsyncRedis):
    """Redis double whose stream writes always fail, as when the broker is unreachable."""

    async def xadd(self, *args, **kwargs):
        raise ConnectionError("redis unavailable (test double)")


def _stream_events(mock_redis: MockAsyncRedis, stream: str) -> list:
    return [deserialize_event(fields) for _id, fields in mock_redis.streams.get(stream, [])]


def _publish_failures(client: TestClient) -> int:
    return client.get("/healthz").json()["event_publish_failures"]


def _transcribe_body(**extra) -> dict:
    return {
        "speaker_id": "spk-policy-1",
        "speaker_name": "Valeros",
        "session_id": str(uuid.uuid4()),
        "campaign_id": str(uuid.uuid4()),
        "transcript": "I move 3 squares north",
        **extra,
    }


@pytest.fixture
def restore_dynamic_event_bus() -> Generator[None]:
    """Clear the gateway_mcp dynamic tool bus after a test that replaces it."""
    yield
    set_dynamic_event_bus(None)


@pytest.fixture
def production_engine_client(
    monkeypatch: pytest.MonkeyPatch, mock_redis: MockAsyncRedis, tmp_path: Path
) -> Generator[TestClient]:
    """Voice app wired to the production engine, forced unavailable through settings."""
    monkeypatch.setenv("RUNEFOBLE_VOICE_STT_MODEL_SIZE", "runefoble-missing-model")
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("HF_HOME", str(tmp_path / "hf-cache"))
    set_streaming_pipeline(None)
    voice_set_event_bus(RedisStreamsEventBus(client=mock_redis))
    yield TestClient(voice_app, headers=voice_auth_headers())
    voice_set_event_bus(None)
    set_streaming_pipeline(None)


def test_transcribe_returns_503_and_records_nothing_when_player_event_unpublished(
    client: TestClient, mock_redis: MockAsyncRedis
):
    """Domain state: a spoken action whose event cannot be published fails with 503."""
    voice_set_event_bus(RedisStreamsEventBus(client=FailingRedis()))

    resp = client.post(TRANSCRIBE_URL, json=_transcribe_body())

    assert resp.status_code == 503, resp.text
    assert resp.json()["event_type"] == "PlayerSpokeEvent"
    assert not [
        e for e in _stream_events(mock_redis, SESSION_STREAM) if isinstance(e, PlayerSpokeEvent)
    ]


def test_notification_route_succeeds_and_counts_each_failed_delivery(client: TestClient):
    """Notification: barge-in events succeed when Redis is down. Each failed delivery is counted."""
    speech_pcm = generate_pcm_sine(duration_ms=100, freq=440.0, amplitude=9000)
    payload = {
        "session_id": "sess-policy-barge",
        "speaker_id": "spk-marcus",
        "speaker_name": "Marcus",
        "audio_base64": base64.b64encode(speech_pcm).decode("ascii"),
        "fade_duration_ms": 20.0,
        "energy_threshold": 350.0,
    }
    before = _publish_failures(client)
    voice_set_event_bus(RedisStreamsEventBus(client=FailingRedis()))

    resp = client.post(BARGE_IN_URL, json=payload)

    assert resp.status_code == 200, resp.text
    assert resp.json()["barge_in_detected"] is True
    # Two events, each published to two streams. Every failed delivery adds one.
    assert _publish_failures(client) == before + 4


def test_engine_failure_on_transcribe_route_publishes_transcription_failed(
    production_engine_client: TestClient, mock_redis: MockAsyncRedis
):
    """A transcription engine error is published as VoiceTranscriptionFailed, then returns 503."""
    body = _transcribe_body(
        audio_base64=base64.b64encode(generate_pcm_sine(duration_ms=300)).decode("ascii"),
    )
    body.pop("transcript")

    resp = production_engine_client.post(TRANSCRIBE_URL, json=body)

    assert resp.status_code == 503, resp.text
    assert resp.json()["detail"]["engine"] == "faster-whisper"
    failures = [
        e
        for e in _stream_events(mock_redis, VOICE_STREAM)
        if isinstance(e, VoiceTranscriptionFailed)
    ]
    assert len(failures) == 1
    assert failures[0].engine == "faster-whisper"
    assert failures[0].speaker_name == "Valeros"
    assert not [
        e for e in _stream_events(mock_redis, SESSION_STREAM) if isinstance(e, PlayerSpokeEvent)
    ]


def test_stream_chunk_publish_failure_is_reported_on_socket_and_not_recorded(
    client: TestClient, mock_redis: MockAsyncRedis
):
    """Domain state on the stream path: the client gets a publish_failed frame, nothing is kept."""
    voice_set_event_bus(RedisStreamsEventBus(client=FailingRedis()))
    chunk = {
        "session_id": str(uuid.uuid4()),
        "speaker_id": "spk-stream-policy",
        "speaker_name": "Valeros",
        "audio_data": base64.b64encode(generate_pcm_sine(duration_ms=300)).decode("ascii"),
        "is_final": True,
    }

    with client.websocket_connect(
        f"/api/v1/voice/stream/ws/{chunk['session_id']}/spk-stream-policy",
        subprotocols=voice_ws_subprotocols(),
    ) as ws:
        ws.send_json(chunk)
        frame = ws.receive_json()

    assert frame["status"] == "publish_failed"
    assert frame["event_type"] == "PlayerSpokeEvent"
    assert not [
        e for e in _stream_events(mock_redis, SESSION_STREAM) if isinstance(e, PlayerSpokeEvent)
    ]


def test_dropped_dynamic_tool_event_is_counted_on_gateway_mcp_healthz(
    restore_dynamic_event_bus: None,
):
    """Dropped system events are counted and reported on the gateway_mcp health route."""
    client = TestClient(mcp.streamable_http_app())
    before = client.get("/healthz").json()["event_publish_failures"]
    set_dynamic_event_bus(RedisStreamsEventBus(client=FailingRedis()))
    event = DynamicToolUnregisteredEvent(tool_name="probe", unregistered_by=None, campaign_id=None)

    asyncio.run(publish_system_event(event))

    body = client.get("/healthz").json()
    assert body["service"] == "gateway_mcp"
    assert body["event_publish_failures"] == before + 1


def test_gateway_mcp_standalone_injects_redis_streams_bus(restore_dynamic_event_bus: None):
    """Standalone gateway_mcp injects the Redis bus that dynamic tool events use."""
    configure_dynamic_event_bus(PlatformSettings(redis_url="redis://redis.example:6379/4"))

    bus = get_dynamic_event_bus()
    assert isinstance(bus, RedisStreamsEventBus)
    assert bus.redis_url == "redis://redis.example:6379/4"


def test_gateway_mcp_standalone_refuses_missing_redis_url(restore_dynamic_event_bus: None):
    """Standalone gateway_mcp fails at start-up when no Redis URL is configured."""
    with pytest.raises(EventBusUnavailableError, match="RUNEFOBLE_REDIS_URL"):
        configure_dynamic_event_bus(PlatformSettings(redis_url=""))


@pytest.mark.parametrize(
    "module_path",
    ["campaign_lore.main", "rules_compendium.main", "inference_worker.api"],
)
def test_service_healthz_reports_publish_failure_counter(module_path: str):
    """Each service health route reports the publish failure counter."""
    import importlib

    app = importlib.import_module(module_path).app
    body = TestClient(app).get("/healthz").json()

    assert isinstance(body["event_publish_failures"], int)
