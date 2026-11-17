"""Blackbox tests for the transcribe route input contract (TASK-0602).

Drive only POST /api/v1/voice/transcribe and read the Redis Streams. The fixture
speech engine sits at the composition root. The production engine is forced
unavailable through settings. The route never invents player text.
"""

from __future__ import annotations

import base64
import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from runefoble_events.events import PlayerSpokeEvent
from runefoble_platform.redis_bus import MockAsyncRedis, RedisStreamsEventBus, deserialize_event
from voice_agent.main import app as voice_app
from voice_agent.main import set_event_bus as voice_set_event_bus
from voice_agent.stt import set_streaming_pipeline

from tests.helpers.audio_synth import generate_pcm_sine

TRANSCRIBE_URL = "/api/v1/voice/transcribe"
SESSION_STREAM = "runefoble.events.session"
WATCHER_STREAM = "runefoble.events.watcher"
FORBIDDEN_PHRASE = "I inspect my surroundings."


def _body(**extra) -> dict:
    return {
        "speaker_id": "spk-transcribe-1",
        "speaker_name": "Valeros",
        "session_id": str(uuid.uuid4()),
        "campaign_id": str(uuid.uuid4()),
        **extra,
    }


def _pcm_b64(duration_ms: int = 300) -> str:
    return base64.b64encode(generate_pcm_sine(duration_ms=duration_ms)).decode("ascii")


def _stream_events(mock_redis: MockAsyncRedis, stream: str) -> list:
    return [deserialize_event(fields) for _id, fields in mock_redis.streams.get(stream, [])]


def _player_spoke_events(mock_redis: MockAsyncRedis) -> list[PlayerSpokeEvent]:
    return [
        e for e in _stream_events(mock_redis, SESSION_STREAM) if isinstance(e, PlayerSpokeEvent)
    ]


@pytest.fixture
def production_engine_client(
    monkeypatch: pytest.MonkeyPatch, mock_redis: MockAsyncRedis
) -> Generator[TestClient]:
    """Voice app wired to the production engine, forced unavailable through settings.

    An unknown model size makes faster-whisper fail to load without network access.
    """
    monkeypatch.setenv("RUNEFOBLE_VOICE_STT_MODEL_SIZE", "runefoble-missing-model")
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    set_streaming_pipeline(None)
    voice_set_event_bus(RedisStreamsEventBus(client=mock_redis))
    yield TestClient(voice_app)
    voice_set_event_bus(None)
    set_streaming_pipeline(None)


def test_request_without_text_or_audio_is_rejected(client: TestClient, mock_redis: MockAsyncRedis):
    """No transcript and no audio returns 422. No player action is created."""
    resp = client.post(TRANSCRIBE_URL, json=_body())

    assert resp.status_code == 422, resp.text
    assert FORBIDDEN_PHRASE not in resp.text
    assert _player_spoke_events(mock_redis) == []
    assert WATCHER_STREAM not in mock_redis.streams


@pytest.mark.parametrize("blank", ["", "   "])
def test_blank_transcript_without_audio_is_rejected(
    client: TestClient, mock_redis: MockAsyncRedis, blank: str
):
    """A blank transcript is not player speech. It returns 422 and publishes nothing."""
    resp = client.post(TRANSCRIBE_URL, json=_body(transcript=blank))

    assert resp.status_code == 422, resp.text
    assert _player_spoke_events(mock_redis) == []
    assert WATCHER_STREAM not in mock_redis.streams


def test_audio_is_decoded_and_transcribed_by_engine(
    client: TestClient, mock_redis: MockAsyncRedis, speech_engine
):
    """Audio goes through the STT port. The engine text becomes the player action."""
    speech_engine.script("step two squares north")

    resp = client.post(TRANSCRIBE_URL, json=_body(audio_base64=_pcm_b64()))

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["transcript"] == "step two squares north"
    assert data["source"] == "audio"
    assert [e.transcript for e in _player_spoke_events(mock_redis)] == ["step two squares north"]


def test_client_text_is_labelled_client_text(client: TestClient, mock_redis: MockAsyncRedis):
    """Typed text is used as given and labelled with its source."""
    resp = client.post(TRANSCRIBE_URL, json=_body(transcript="advance 2 east"))

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["transcript"] == "advance 2 east"
    assert data["source"] == "client_text"
    assert [e.transcript for e in _player_spoke_events(mock_redis)] == ["advance 2 east"]


def test_malformed_audio_is_rejected(client: TestClient, mock_redis: MockAsyncRedis):
    """Audio that is not valid base64 returns 422. No event is published."""
    resp = client.post(TRANSCRIBE_URL, json=_body(audio_base64="!!!not_valid_base64!!!"))

    assert resp.status_code == 422, resp.text
    assert _player_spoke_events(mock_redis) == []


def test_silent_audio_publishes_no_player_action(
    client: TestClient, mock_redis: MockAsyncRedis, speech_engine
):
    """When the engine hears no words, no player action is created."""
    speech_engine.script("")

    resp = client.post(TRANSCRIBE_URL, json=_body(audio_base64=_pcm_b64()))

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["transcript"] == ""
    assert data["source"] == "audio"
    assert data["event_id"] is None
    assert _player_spoke_events(mock_redis) == []
    assert WATCHER_STREAM not in mock_redis.streams


def test_unavailable_engine_returns_503_and_publishes_nothing(
    production_engine_client: TestClient, mock_redis: MockAsyncRedis
):
    """When the production engine cannot transcribe, the route fails with 503."""
    resp = production_engine_client.post(TRANSCRIBE_URL, json=_body(audio_base64=_pcm_b64()))

    assert resp.status_code == 503, resp.text
    detail = resp.json()["detail"]
    assert detail["error"] == "speech_engine_unavailable"
    assert detail["engine"] == "faster-whisper"
    assert FORBIDDEN_PHRASE not in resp.text
    assert _player_spoke_events(mock_redis) == []
