"""Blackbox TDD tests for Streaming Voice VAD and Audio Chunking Pipeline.

Verifies silence chunk rejection, speech onset buffering, sub-250ms trailing silence
segmentation, and standard 44-byte WAV container ingestion.
"""

from __future__ import annotations

import base64
import uuid

from fastapi.testclient import TestClient
from runefoble_events.events import PlayerSpokeEvent
from runefoble_platform.redis_bus import (
    MockAsyncRedis,
    deserialize_event,
)

from tests.helpers.audio_synth import (
    generate_pcm_silence,
    generate_pcm_sine,
    generate_wav_sine,
)


def test_silence_chunk_rejected_without_events(client: TestClient, mock_redis: MockAsyncRedis):
    """Silence chunks below VAD energy threshold produce no false positive transcription or events."""
    silence_pcm = generate_pcm_silence(duration_ms=200)
    silence_b64 = base64.b64encode(silence_pcm).decode("ascii")

    session_id = str(uuid.uuid4())
    resp = client.post(
        "/api/v1/voice/stream/chunk",
        json={
            "session_id": session_id,
            "speaker_id": "spk-silence-1",
            "speaker_name": "Quiet Player",
            "audio_data": silence_b64,
            "sample_rate": 16000,
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["speech_detected"] is False
    assert data["utterance_complete"] is False
    assert data["transcript"] is None
    assert data["vad_state"] == "silence"

    # Assert no PlayerSpokeEvent was emitted
    assert "runefoble.events.session" not in mock_redis.streams


def test_speech_onset_and_accumulation(client: TestClient, mock_redis: MockAsyncRedis):
    """Active speech frames are detected and buffered without premature utterance completion."""
    speech_pcm = generate_pcm_sine(duration_ms=100)
    speech_b64 = base64.b64encode(speech_pcm).decode("ascii")

    session_id = str(uuid.uuid4())
    resp = client.post(
        "/api/v1/voice/stream/chunk",
        json={
            "session_id": session_id,
            "speaker_id": "spk-speech-1",
            "speaker_name": "Valeros",
            "audio_data": speech_b64,
            "sample_rate": 16000,
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["speech_detected"] is True
    assert data["utterance_complete"] is False
    assert data["transcript"] is None
    assert data["vad_state"] == "speech_active"
    assert data["buffer_duration_ms"] > 0

    assert "runefoble.events.session" not in mock_redis.streams


def test_sub_250ms_silence_triggers_utterance_and_event(
    client: TestClient, mock_redis: MockAsyncRedis
):
    """Trailing silence exceeding the 200ms threshold (< 250ms SLA) triggers transcription and PlayerSpokeEvent."""
    session_id = str(uuid.uuid4())
    campaign_id = str(uuid.uuid4())

    # 1. Stream 300ms of active speech
    speech_pcm = generate_pcm_sine(duration_ms=300)
    client.post(
        "/api/v1/voice/stream/chunk",
        json={
            "session_id": session_id,
            "speaker_id": "spk-kyra-1",
            "speaker_name": "Kyra",
            "campaign_id": campaign_id,
            "audio_data": base64.b64encode(speech_pcm).decode("ascii"),
        },
    )

    # 2. Stream 200ms of trailing silence (< 250ms threshold)
    silence_pcm = generate_pcm_silence(duration_ms=200)
    resp = client.post(
        "/api/v1/voice/stream/chunk",
        json={
            "session_id": session_id,
            "speaker_id": "spk-kyra-1",
            "speaker_name": "Kyra",
            "campaign_id": campaign_id,
            "audio_data": base64.b64encode(silence_pcm).decode("ascii"),
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["utterance_complete"] is True
    assert data["transcript"] is not None
    assert len(data["transcript"]) > 0
    assert data["vad_state"] == "utterance_complete"
    assert data["latency_ms"] < 250.0

    # 3. Assert PlayerSpokeEvent on Redis Streams
    assert "runefoble.events.session" in mock_redis.streams
    entries = mock_redis.streams["runefoble.events.session"]
    assert len(entries) == 1
    _eid, fields = entries[0]
    event = deserialize_event(fields)
    assert isinstance(event, PlayerSpokeEvent)
    assert event.speaker_id == "spk-kyra-1"
    assert event.speaker_name == "Kyra"
    assert event.transcript == data["transcript"]


def test_wav_container_ingestion(client: TestClient, mock_redis: MockAsyncRedis):
    """Audio packaged inside a standard 44-byte WAV header is correctly decoded and processed."""
    wav_bytes = generate_wav_sine(duration_ms=200)
    wav_b64 = base64.b64encode(wav_bytes).decode("ascii")

    session_id = str(uuid.uuid4())
    resp = client.post(
        "/api/v1/voice/stream/chunk",
        json={
            "session_id": session_id,
            "speaker_id": "spk-wav-1",
            "speaker_name": "Ezren",
            "audio_data": wav_b64,
            "is_final": True,
            "mock_transcript": "I cast magic missile",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["utterance_complete"] is True
    assert data["transcript"] == "I cast magic missile"

    assert "runefoble.events.session" in mock_redis.streams
