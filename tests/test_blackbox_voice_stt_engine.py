"""Blackbox tests for the production speech-to-text engine (TASK-0600).

Drive only the public voice HTTP routes and read the Redis Streams.
The tests never patch the transcriber and never read private pipeline state.
"""

from __future__ import annotations

import asyncio
import base64
import uuid
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from runefoble_events.events import PlayerSpokeEvent, VoiceTranscriptionFailed
from runefoble_platform.redis_bus import RedisStreamsEventBus, deserialize_event
from voice_agent.main import app as voice_app
from voice_agent.main import set_event_bus as voice_set_event_bus
from voice_agent.stt import set_streaming_pipeline
from voice_agent.synthesis_engine import set_speech_synthesizer

from tests.helpers.audio_synth import generate_pcm_silence, generate_pcm_sine
from tests.helpers.fixture_transcriber import FIXTURE_TRANSCRIPT
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.voice_grants import grant_voice_session
from tests.helpers.voice_identity import voice_auth_headers

pytestmark = pytest.mark.usefixtures("trusted_voice_issuer")

CHUNK_URL = "/api/v1/voice/stream/chunk"


def _post_speech_then_silence(client: TestClient, session_id: str) -> list:
    """Send one speech chunk, then one silence chunk that completes the utterance."""
    speech = {
        "session_id": session_id,
        "speaker_id": "spk-stt-1",
        "speaker_name": "Valeros",
        "audio_data": base64.b64encode(generate_pcm_sine(duration_ms=300)).decode("ascii"),
    }
    silence = {
        "session_id": session_id,
        "speaker_id": "spk-stt-1",
        "speaker_name": "Valeros",
        "audio_data": base64.b64encode(generate_pcm_silence(duration_ms=200)).decode("ascii"),
    }
    client.post(CHUNK_URL, json=speech)
    return [client.post(CHUNK_URL, json=silence)]


def _stream_events(mock_redis: MockAsyncRedis, stream: str) -> list:
    return [deserialize_event(fields) for _id, fields in mock_redis.streams.get(stream, [])]


@pytest.fixture
def production_engine_client(
    monkeypatch: pytest.MonkeyPatch, mock_redis: MockAsyncRedis, tmp_path: Path
) -> Generator[TestClient]:
    """Voice app wired to the production engine, forced unavailable through settings.

    An unknown model size makes faster-whisper fail to load without any network access.
    The speech binary is a stub that answers `--version`, so only the STT engine is not ready.
    """
    monkeypatch.setenv("RUNEFOBLE_VOICE_STT_MODEL_SIZE", "runefoble-missing-model")
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    stub = tmp_path / "espeak-ng-version"
    stub.write_text("#!/bin/sh\necho 'eSpeak NG stub'\nexit 0\n", encoding="utf-8")
    stub.chmod(0o755)
    monkeypatch.setenv("RUNEFOBLE_VOICE_TTS_BINARY", str(stub))
    set_speech_synthesizer(None)
    set_streaming_pipeline(None)
    voice_set_event_bus(RedisStreamsEventBus(client=mock_redis))
    yield TestClient(voice_app, headers=voice_auth_headers())
    voice_set_event_bus(None)
    set_streaming_pipeline(None)
    set_speech_synthesizer(None)


def test_unavailable_engine_returns_error_and_publishes_no_player_spoke(
    production_engine_client: TestClient, mock_redis: MockAsyncRedis
):
    """A completed utterance fails explicitly when the production engine cannot transcribe it."""
    session_id = str(uuid.uuid4())
    asyncio.run(grant_voice_session(session_id, players=["spk-stt-1", "spk-forge-1"]))

    (resp,) = _post_speech_then_silence(production_engine_client, session_id)

    assert resp.status_code == 503, resp.text
    body = resp.json()["detail"]
    assert body["error"] == "speech_engine_unavailable"
    assert body["engine"] == "faster-whisper"
    assert "I move 3 squares north" not in resp.text

    session_events = _stream_events(mock_redis, "runefoble.events.session")
    assert not [e for e in session_events if isinstance(e, PlayerSpokeEvent)]

    voice_events = _stream_events(mock_redis, "runefoble.events.voice")
    failures = [e for e in voice_events if isinstance(e, VoiceTranscriptionFailed)]
    assert len(failures) == 1
    assert failures[0].engine == "faster-whisper"
    assert failures[0].speaker_name == "Valeros"


def test_utterance_uses_configured_engine_transcript(
    client: TestClient, mock_redis: MockAsyncRedis
):
    """The transcript returned to the caller comes from the configured engine, not a canned phrase."""
    session_id = str(uuid.uuid4())
    asyncio.run(grant_voice_session(session_id, players=["spk-stt-1", "spk-forge-1"]))

    (resp,) = _post_speech_then_silence(client, session_id)

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["utterance_complete"] is True
    assert data["transcript"] == FIXTURE_TRANSCRIPT

    player_events = [
        e
        for e in _stream_events(mock_redis, "runefoble.events.session")
        if isinstance(e, PlayerSpokeEvent)
    ]
    assert [e.transcript for e in player_events] == [FIXTURE_TRANSCRIPT]


def test_client_supplied_transcript_is_ignored(client: TestClient, mock_redis: MockAsyncRedis):
    """A caller cannot inject a transcript. The configured engine always decides the text."""
    session_id = str(uuid.uuid4())
    asyncio.run(grant_voice_session(session_id, players=["spk-stt-1", "spk-forge-1"]))
    forged = "I move 3 squares north"
    speech = {
        "session_id": session_id,
        "speaker_id": "spk-forge-1",
        "speaker_name": "Valeros",
        "audio_data": base64.b64encode(generate_pcm_sine(duration_ms=300)).decode("ascii"),
        "mock_transcript": forged,
    }
    silence = {
        "session_id": session_id,
        "speaker_id": "spk-forge-1",
        "speaker_name": "Valeros",
        "audio_data": base64.b64encode(generate_pcm_silence(duration_ms=200)).decode("ascii"),
        "mock_transcript": forged,
    }
    client.post(CHUNK_URL, json=speech)
    resp = client.post(CHUNK_URL, json=silence)

    assert resp.status_code == 200, resp.text
    assert resp.json()["transcript"] == FIXTURE_TRANSCRIPT
    player_events = [
        e
        for e in _stream_events(mock_redis, "runefoble.events.session")
        if isinstance(e, PlayerSpokeEvent)
    ]
    assert [e.transcript for e in player_events] == [FIXTURE_TRANSCRIPT]


def test_health_reports_active_stt_engine(production_engine_client: TestClient):
    """The health route names the active speech engine."""
    resp = production_engine_client.get("/healthz")

    assert resp.status_code == 200
    assert resp.json()["stt_engine"] == "faster-whisper"
