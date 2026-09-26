"""Blackbox TDD tests for Sub-500ms Streaming Audio Whisper & VAD Pipeline (TASK-0039).

Verifies streaming PCM/WAV ingestion, Silero-compatible sub-250ms silence VAD segmentation,
deterministic Whisper acoustic transcription, Redis Streams CloudEvents dispatch (PlayerSpokeEvent),
Watcher intent orchestration (SpeechIntentParsed), and sub-500ms end-to-end latency budget.
"""

from __future__ import annotations

import base64
import math
import struct
import time
import uuid

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from runefoble_events.events import (
    PlayerSpokeEvent,
    SpeechIntentParsed,
)
from runefoble_platform.redis_bus import (
    MockAsyncRedis,
    RedisStreamsEventBus,
    deserialize_event,
)
from the_watcher.main import app as watcher_app
from the_watcher.main import set_event_bus as watcher_set_event_bus
from voice_agent.main import (
    app as voice_app,
)
from voice_agent.main import (
    set_event_bus as voice_set_event_bus,
)
from voice_agent.main import (
    set_watcher_client,
)
from voice_agent.stt import get_streaming_pipeline


def generate_pcm_sine(
    duration_ms: int = 100,
    freq: float = 440.0,
    sample_rate: int = 16000,
    amplitude: int = 8000,
) -> bytes:
    """Generate 16-bit mono signed PCM sine wave simulating vocal audio."""
    num_samples = int(sample_rate * (duration_ms / 1000.0))
    samples = [
        int(amplitude * math.sin(2.0 * math.pi * freq * i / sample_rate))
        for i in range(num_samples)
    ]
    return struct.pack(f"<{num_samples}h", *samples)


def generate_pcm_silence(duration_ms: int = 100, sample_rate: int = 16000) -> bytes:
    """Generate 16-bit mono signed PCM silence (zero amplitude)."""
    num_samples = int(sample_rate * (duration_ms / 1000.0))
    return bytes(num_samples * 2)


def generate_wav_sine(
    duration_ms: int = 100,
    freq: float = 440.0,
    sample_rate: int = 16000,
    amplitude: int = 8000,
) -> bytes:
    """Generate a standard 44-byte WAV header containing 16-bit mono PCM."""
    pcm_bytes = generate_pcm_sine(duration_ms, freq, sample_rate, amplitude)
    num_channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * (bits_per_sample // 8)
    block_align = num_channels * (bits_per_sample // 8)
    data_size = len(pcm_bytes)
    chunk_size = 36 + data_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        chunk_size,
        b"WAVE",
        b"fmt ",
        16,  # Subchunk1Size for PCM
        1,  # AudioFormat (PCM)
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )
    return header + pcm_bytes


@pytest.fixture
def mock_redis() -> MockAsyncRedis:
    return MockAsyncRedis()


@pytest.fixture
def shared_event_bus(mock_redis: MockAsyncRedis) -> RedisStreamsEventBus:
    bus = RedisStreamsEventBus(client=mock_redis)
    voice_set_event_bus(bus)
    watcher_set_event_bus(bus)
    yield bus
    voice_set_event_bus(None)
    watcher_set_event_bus(None)


@pytest.fixture
def client(shared_event_bus: RedisStreamsEventBus) -> TestClient:
    get_streaming_pipeline().reset_all()
    # Wire the watcher ASGI transport directly for inter-service communication
    watcher_client = AsyncClient(transport=ASGITransport(app=watcher_app), base_url="http://test")
    set_watcher_client(watcher_client)
    return TestClient(voice_app)


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


def test_end_to_end_streaming_speech_to_intent_latency_budget(
    client: TestClient, mock_redis: MockAsyncRedis
):
    """Verifies end-to-end streaming speech transcription and Watcher intent parsing strictly within 500ms."""
    session_id = str(uuid.uuid4())
    campaign_id = str(uuid.uuid4())

    speech_pcm = generate_pcm_sine(duration_ms=300)
    silence_pcm = generate_pcm_silence(duration_ms=200)

    # 1. Send speech
    client.post(
        "/api/v1/voice/stream/chunk",
        json={
            "session_id": session_id,
            "speaker_id": "spk-valeros-1",
            "speaker_name": "Valeros",
            "campaign_id": campaign_id,
            "audio_data": base64.b64encode(speech_pcm).decode("ascii"),
            "mock_transcript": "advance 2 east",
        },
    )

    # 2. Send silence to trigger completion and measure roundtrip
    t0 = time.perf_counter()
    resp = client.post(
        "/api/v1/voice/stream/chunk",
        json={
            "session_id": session_id,
            "speaker_id": "spk-valeros-1",
            "speaker_name": "Valeros",
            "campaign_id": campaign_id,
            "audio_data": base64.b64encode(silence_pcm).decode("ascii"),
            "mock_transcript": "advance 2 east",
        },
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["utterance_complete"] is True
    assert data["transcript"] == "advance 2 east"
    assert data["watcher_intent"] is not None
    assert data["watcher_intent"]["action_type"] == "move"
    assert data["latency_ms"] < 250.0
    assert elapsed_ms < 500.0, f"Roundtrip {elapsed_ms:.2f}ms exceeded 500ms budget"

    # 3. Assert PlayerSpokeEvent in runefoble.events.session
    assert "runefoble.events.session" in mock_redis.streams

    # 4. Assert SpeechIntentParsed in runefoble.events.watcher
    assert "runefoble.events.watcher" in mock_redis.streams
    watcher_entries = mock_redis.streams["runefoble.events.watcher"]
    intent_events = [
        deserialize_event(f)
        for _, f in watcher_entries
        if isinstance(deserialize_event(f), SpeechIntentParsed)
    ]
    assert len(intent_events) >= 1
    intent_event = intent_events[0]
    assert intent_event.speaker_name == "Valeros"
    assert intent_event.action_type == "move"
    assert intent_event.raw_transcript == "advance 2 east"


def test_continuous_stream_over_websocket_frontdoor(client: TestClient, mock_redis: MockAsyncRedis):
    """Continuous PCM audio frame streaming via WebSocket frontdoor dispatches events upon utterance completion."""
    session_id = str(uuid.uuid4())
    speaker_id = "spk-ws-valeros"

    with client.websocket_connect(
        f"/api/v1/voice/stream/ws/{session_id}/{speaker_id}?speaker_name=Valeros"
    ) as ws:
        # Frame 1: 200ms speech
        speech_pcm = generate_pcm_sine(duration_ms=200)
        ws.send_bytes(speech_pcm)
        res1 = ws.receive_json()
        assert res1["speech_detected"] is True
        assert res1["utterance_complete"] is False

        # Frame 2: 200ms silence (< 250ms threshold)
        silence_pcm = generate_pcm_silence(duration_ms=200)
        ws.send_bytes(silence_pcm)
        res2 = ws.receive_json()
        assert res2["utterance_complete"] is True
        assert res2["transcript"] is not None
        assert res2["latency_ms"] < 250.0

    # Verify event bus received PlayerSpokeEvent
    assert "runefoble.events.session" in mock_redis.streams
    _id, fields = mock_redis.streams["runefoble.events.session"][0]
    event = deserialize_event(fields)
    assert isinstance(event, PlayerSpokeEvent)
    assert event.speaker_id == speaker_id
    assert event.speaker_name == "Valeros"


def test_forced_completion_via_is_final(client: TestClient, mock_redis: MockAsyncRedis):
    """Passing is_final=True immediately flushes and transcribes active speech without trailing silence."""
    speech_pcm = generate_pcm_sine(duration_ms=200)
    speech_b64 = base64.b64encode(speech_pcm).decode("ascii")

    session_id = str(uuid.uuid4())
    resp = client.post(
        "/api/v1/voice/stream/chunk",
        json={
            "session_id": session_id,
            "speaker_id": "spk-final-1",
            "speaker_name": "Merisiel",
            "audio_data": speech_b64,
            "is_final": True,
            "mock_transcript": "I cast shield",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["utterance_complete"] is True
    assert data["transcript"] == "I cast shield"

    assert "runefoble.events.session" in mock_redis.streams


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


def test_multi_speaker_buffer_isolation(client: TestClient, mock_redis: MockAsyncRedis):
    """Multiple participants streaming audio concurrently maintain isolated ring buffers and VAD states."""
    session_id = str(uuid.uuid4())

    speech_pcm = generate_pcm_sine(duration_ms=200)
    silence_pcm = generate_pcm_silence(duration_ms=200)

    # Kyra speaks
    client.post(
        "/api/v1/voice/stream/chunk",
        json={
            "session_id": session_id,
            "speaker_id": "spk-kyra",
            "speaker_name": "Kyra",
            "audio_data": base64.b64encode(speech_pcm).decode("ascii"),
            "mock_transcript": "heal Valeros",
        },
    )

    # Valeros is silent
    res_valeros = client.post(
        "/api/v1/voice/stream/chunk",
        json={
            "session_id": session_id,
            "speaker_id": "spk-valeros",
            "speaker_name": "Valeros",
            "audio_data": base64.b64encode(silence_pcm).decode("ascii"),
        },
    )
    assert res_valeros.json()["speech_detected"] is False
    assert res_valeros.json()["utterance_complete"] is False

    # Kyra completes utterance via trailing silence
    res_kyra = client.post(
        "/api/v1/voice/stream/chunk",
        json={
            "session_id": session_id,
            "speaker_id": "spk-kyra",
            "speaker_name": "Kyra",
            "audio_data": base64.b64encode(silence_pcm).decode("ascii"),
            "mock_transcript": "heal Valeros",
        },
    )
    assert res_kyra.json()["utterance_complete"] is True
    assert res_kyra.json()["transcript"] == "heal Valeros"

    # Only Kyra's event was emitted
    assert len(mock_redis.streams["runefoble.events.session"]) == 1
    event = deserialize_event(mock_redis.streams["runefoble.events.session"][0][1])
    assert event.speaker_id == "spk-kyra"
